"""
Flask backend for the Fake News Detection web UI.

Features:
- /api/check -> 5-layer fake-news verification
- /api/explain -> LIME / SHAP Explainable AI
- /api/chat -> AI chatbot
- /api/live-feed -> live headlines
- /api/history -> verification history
- /api/history/<id> DELETE -> delete one history record
- /api/stats -> statistics

Run:
    python webapp/app.py

Open:
    http://127.0.0.1:5000
"""

import os
import sys
import json

# ============================================================
# PROJECT ROOT
# ============================================================

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

# ============================================================
# FLASK
# ============================================================

from flask import (
    Flask,
    request,
    jsonify,
    render_template
)

# ============================================================
# PROJECT MODULES
# ============================================================

from src.utils import (
    MODELS_DIR,
    OUTPUT_DIR
)

from src.realtime_news import (
    load_best_model,
    predict_headlines,
    fetch_live_headlines
)

from src.verify_news import (
    verify_headline
)

from src.plausibility_check import (
    check_plausibility
)

from src.factcheck import (
    search_fact_checks
)

from src.llm_analysis import (
    analyze_with_llm
)

from src.database import (
    log_check,
    get_history,
    get_stats,
    delete_history
)

from src.explain import (
    explain_headline
)

from src.chatbot import (
    chat_reply
)

# ============================================================
# APP
# ============================================================

app = Flask(__name__)

# ============================================================
# MODEL CACHE
# ============================================================

_best_model_name = None
_best_model = None

# ============================================================
# LOAD MODEL
# ============================================================

def get_model():
    global _best_model_name
    global _best_model

    if _best_model is None:
        best_model_path = os.path.join(
            OUTPUT_DIR,
            "best_model.json"
        )

        if not os.path.exists(best_model_path):
            raise FileNotFoundError(
                "best_model.json was not found in OUTPUT_DIR."
            )

        with open(
            best_model_path,
            "r",
            encoding="utf-8"
        ) as f:
            config = json.load(f)

        _best_model_name = config["best_model"]

        _best_model = load_best_model(
            _best_model_name,
            MODELS_DIR
        )

    return _best_model_name, _best_model

# ============================================================
# HOME
# ============================================================

@app.route("/")
def index():
    return render_template("index.html")

# ============================================================
# VERIFY NEWS
# ============================================================

@app.route(
    "/api/check",
    methods=["POST"]
)
def api_check():
    data = (
        request
        .get_json(
            force=True,
            silent=True
        )
        or {}
    )

    headline = str(
        data.get(
            "headline",
            ""
        )
    ).strip()

    if not headline:
        return jsonify({
            "error": "Headline is empty"
        }), 400

    try:
        model_name, best_model = get_model()

        # ====================================================
        # LAYER 1
        # TRUSTED SOURCE VERIFICATION
        # ====================================================

        verification = verify_headline(headline)

        if verification.get("verified"):
            sources = [
                item.get(
                    "source",
                    "Unknown source"
                )
                for item in verification.get(
                    "matched_sources",
                    []
                )
            ]

            log_check(
                headline,
                "REAL",
                "verified",
                f"sources: {sources}"
            )

            return jsonify({
                "headline": headline,
                "verdict": "REAL",
                "mode": "verified",
                "sources": sources,
                "reason": "The headline was matched with trusted news sources."
            })

        # ====================================================
        # LAYER 2
        # FACT CHECK
        # ====================================================

        fc = search_fact_checks(headline)

        if fc.get("found"):
            reviews = fc.get("reviews", [])

            if reviews:
                top = reviews[0]

                rating = str(
                    top.get(
                        "rating",
                        ""
                    )
                )

                rating_lower = rating.lower()

                fake_words = [
                    "false",
                    "fake",
                    "misleading",
                    "pants",
                    "incorrect",
                    "not true"
                ]

                verdict = (
                    "FAKE"
                    if any(
                        word in rating_lower
                        for word in fake_words
                    )
                    else "REAL"
                )

                publisher = top.get(
                    "publisher",
                    "Fact-check source"
                )

                log_check(
                    headline,
                    verdict,
                    "fact_checked",
                    f"{publisher}: {rating}"
                )

                response = {
                    "headline": headline,
                    "verdict": verdict,
                    "mode": "fact_checked",
                    "publisher": publisher,
                    "rating": rating
                }

                if top.get("url"):
                    response["url"] = top["url"]

                return jsonify(response)

        # ====================================================
        # LAYER 3
        # RULE BASED PLAUSIBILITY
        # ====================================================

        plausibility = check_plausibility(headline)

        if plausibility.get("flagged"):
            reason = (
                plausibility.get("reason")
                or
                "Matches common fake-news red-flag patterns."
            )

            log_check(
                headline,
                "FAKE",
                "flagged",
                reason
            )

            return jsonify({
                "headline": headline,
                "verdict": "FAKE",
                "mode": "flagged",
                "reason": reason
            })

        # ====================================================
        # LAYER 4
        # LLM ANALYSIS
        # ====================================================

        llm_result = analyze_with_llm(headline)

        if (
            llm_result.get("available")
            and
            llm_result.get("verdict") == "IMPLAUSIBLE"
        ):
            reason = llm_result.get(
                "reason",
                "The AI reasoning layer found the headline implausible."
            )

            log_check(
                headline,
                "FAKE",
                "llm_flagged",
                reason
            )

            return jsonify({
                "headline": headline,
                "verdict": "FAKE",
                "mode": "llm_flagged",
                "reason": reason
            })

        # ====================================================
        # LAYER 5
        # ML / DL MODEL
        # ====================================================

        model_result = predict_headlines(
            [headline],
            best_model
        )[0]

        prediction = str(
            model_result.get(
                "prediction",
                "UNVERIFIED"
            )
        ).upper()

        confidence = model_result.get("confidence")

        log_check(
            headline,
            prediction,
            "unverified",
            f"confidence: {confidence}"
        )

        return jsonify({
            "headline": headline,
            "verdict": prediction,
            "mode": "unverified",
            "confidence": confidence,
            "model_used": model_name
        })

    except Exception as e:
        print("\n========== CHECK ERROR ==========")
        print(str(e))
        print("==================================\n")

        return jsonify({
            "error": f"Verification failed: {str(e)}"
        }), 500

# ============================================================
# EXPLAINABLE AI
# ============================================================

@app.route(
    "/api/explain",
    methods=["POST"]
)
def api_explain():
    data = (
        request
        .get_json(
            force=True,
            silent=True
        )
        or {}
    )

    headline = str(
        data.get(
            "headline",
            ""
        )
    ).strip()

    method = str(
        data.get(
            "method",
            "lime"
        )
    ).lower().strip()

    if not headline:
        return jsonify({
            "error": "Headline is empty"
        }), 400

    if method not in ("lime", "shap"):
        method = "lime"

    try:
        _, best_model = get_model()

        result = explain_headline(
            headline,
            best_model,
            method=method,
            num_features=12
        )

        return jsonify(result)

    except Exception as e:
        print("\n========== XAI ERROR ==========")
        print(str(e))
        print("================================\n")

        return jsonify({
            "error": f"Explanation failed: {str(e)}"
        }), 500

# ============================================================
# CHATBOT
# ============================================================

@app.route(
    "/api/chat",
    methods=["POST"]
)
def api_chat():
    data = (
        request
        .get_json(
            force=True,
            silent=True
        )
        or {}
    )

    messages = data.get(
        "messages",
        []
    )

    context = data.get("context")

    if not messages:
        return jsonify({
            "error": "No messages provided"
        }), 400

    try:
        result = chat_reply(
            messages,
            context=context
        )

        return jsonify(result)

    except Exception as e:
        print("\n========== CHAT ERROR ==========")
        print(str(e))
        print("================================\n")

        return jsonify({
            "available": False,
            "reply": "Sorry, the chatbot is temporarily unavailable."
        })

# ============================================================
# LIVE FEED
# ============================================================

@app.route("/api/live-feed")
def api_live_feed():
    try:
        model_name, best_model = get_model()

        headlines = fetch_live_headlines(
            limit=8
        )

        results = predict_headlines(
            headlines,
            best_model
        )

        return jsonify({
            "model_used": model_name,
            "results": results
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 502

# ============================================================
# HISTORY
# ============================================================

@app.route("/api/history")
def api_history():
    try:
        return jsonify({
            "history": get_history(15)
        })

    except Exception as e:
        return jsonify({
            "history": [],
            "error": str(e)
        })

# ============================================================
# DELETE HISTORY ITEM
# ============================================================

@app.route(
    "/api/history/<int:check_id>",
    methods=["DELETE"]
)
def api_delete_history(check_id):
    try:
        deleted = delete_history(check_id)

        if not deleted:
            return jsonify({
                "success": False,
                "error": "History record not found."
            }), 404

        return jsonify({
            "success": True,
            "message": "History record deleted successfully."
        })

    except Exception as e:
        print("\n========== DELETE HISTORY ERROR ==========")
        print(str(e))
        print("==========================================\n")

        return jsonify({
            "success": False,
            "error": f"Could not delete history: {str(e)}"
        }), 500

# ============================================================
# STATS
# ============================================================

@app.route("/api/stats")
def api_stats():
    try:
        return jsonify(get_stats())

    except Exception as e:
        return jsonify({
            "total": 0,
            "total_checks": 0,
            "real": 0,
            "fake": 0,
            "unverified": 0,
            "error": str(e)
        })

# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    print("\n==============================================")
    print("        VERIQUEST CHATBOT INITIALIZATION")
    print("==============================================\n")

    try:
        from src.chatbot import (
            GEMINI_API_KEY,
            ANTHROPIC_API_KEY
        )

        print(
            "Gemini API key:",
            "FOUND" if GEMINI_API_KEY else "NOT FOUND"
        )

        print(
            "Anthropic API key:",
            "FOUND" if ANTHROPIC_API_KEY else "NOT FOUND"
        )

    except Exception:
        pass

    print("==============================================\n")
    print("Loading model ...")

    get_model()

    print(
        "Starting server at http://127.0.0.1:5000"
    )

    app.run(
        debug=True,
        port=5000
    )