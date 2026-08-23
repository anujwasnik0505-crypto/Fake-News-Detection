"""
Lightweight REST API for the fake news detector — JSON endpoints, no frontend needed
(the webapp/ folder provides an optional browser UI on top of this same logic).

Five-layer verdict logic:
1. Live trusted-source verification (NewsAPI.org, or free RSS fallback)
2. Google Fact Check Tools API (professional fact-checker database)
3. Rule-based implausibility check
4. LLM reasoning (Claude API), if configured
5. Trained ML/DL model prediction (final fallback)

Every check is logged to a local SQLite database (history.db).

Run with:  python api.py
Then it listens on: http://127.0.0.1:5000

Endpoints:
  GET  /              -> health check
  POST /check         -> body: {"headline": "..."}   returns REAL/FAKE verdict
  GET  /live-feed      -> current headlines auto-classified
  GET  /history        -> recent check history (?limit=20)
  GET  /stats           -> summary stats of all checks
"""
import json
import os

from flask import Flask, request, jsonify

from src.utils import MODELS_DIR, OUTPUT_DIR
from src.realtime_news import load_best_model, predict_headlines, fetch_live_headlines
from src.verify_news import verify_headline
from src.plausibility_check import check_plausibility
from src.factcheck import search_fact_checks
from src.llm_analysis import analyze_with_llm
from src.database import log_check, get_history, get_stats

app = Flask(__name__)

_best_model_name = None
_best_model = None


def get_model():
    global _best_model_name, _best_model
    if _best_model is None:
        with open(os.path.join(OUTPUT_DIR, "best_model.json")) as f:
            _best_model_name = json.load(f)["best_model"]
        _best_model = load_best_model(_best_model_name, MODELS_DIR)
    return _best_model_name, _best_model


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Fake News Detection API is running"})


@app.route("/check", methods=["POST"])
def check():
    data = request.get_json(force=True, silent=True) or {}
    headline = data.get("headline", "").strip()
    if not headline:
        return jsonify({"error": "Provide a 'headline' field in the JSON body"}), 400

    model_name, best_model = get_model()

    verification = verify_headline(headline)
    if verification.get("verified"):
        sources = [m["source"] for m in verification["matched_sources"]]
        log_check(headline, "REAL", "verified", f"sources: {sources}")
        return jsonify({"headline": headline, "verdict": "REAL", "mode": "verified", "sources": sources})

    fc = search_fact_checks(headline)
    if fc.get("found"):
        top = fc["reviews"][0]
        verdict = "FAKE" if any(w in top["rating"].lower() for w in ["false", "fake", "misleading", "pants"]) else "REAL"
        log_check(headline, verdict, "fact_checked", f"{top['publisher']}: {top['rating']}")
        return jsonify({
            "headline": headline, "verdict": verdict, "mode": "fact_checked",
            "publisher": top["publisher"], "rating": top["rating"], "url": top["url"],
        })

    plausibility = check_plausibility(headline)
    if plausibility["flagged"]:
        log_check(headline, "FAKE", "flagged", "matched implausibility patterns")
        return jsonify({
            "headline": headline, "verdict": "FAKE", "mode": "flagged",
            "reason": "Matches common fake-news red-flag patterns",
        })

    llm_result = analyze_with_llm(headline)
    if llm_result["available"] and llm_result["verdict"] == "IMPLAUSIBLE":
        log_check(headline, "FAKE", "llm_flagged", llm_result["reason"])
        return jsonify({
            "headline": headline, "verdict": "FAKE", "mode": "llm_flagged",
            "reason": llm_result["reason"],
        })

    model_result = predict_headlines([headline], best_model)[0]
    log_check(headline, model_result["prediction"], "unverified", f"confidence: {model_result['confidence']}")
    return jsonify({
        "headline": headline,
        "verdict": model_result["prediction"],
        "mode": "unverified",
        "confidence": model_result["confidence"],
        "model_used": model_name,
    })


@app.route("/live-feed", methods=["GET"])
def live_feed():
    model_name, best_model = get_model()
    limit = request.args.get("limit", default=8, type=int)
    try:
        headlines = fetch_live_headlines(limit=limit)
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    results = predict_headlines(headlines, best_model)
    return jsonify({"model_used": model_name, "results": results})


@app.route("/history", methods=["GET"])
def history():
    limit = request.args.get("limit", default=20, type=int)
    return jsonify({"history": get_history(limit)})


@app.route("/stats", methods=["GET"])
def stats():
    return jsonify(get_stats())


if __name__ == "__main__":
    print("Loading model ...")
    get_model()
    print("API running at http://127.0.0.1:5000")
    print("Try: POST http://127.0.0.1:5000/check  with body {\"headline\": \"...\"}")
    app.run(debug=True, port=5000)
