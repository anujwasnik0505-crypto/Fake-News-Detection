"""
Flask backend for the Fake News Detection web UI.

Phase 1:
- 3-way verdict (Likely Real / Suspicious / Uncertain)
- Detailed layer report
- Evidence + source links

Phase 2:
- News URL verification (full article)
- Hindi + multilingual support

Phase 3:
- Claim extraction from article
- Image / screenshot OCR → claim verification

Endpoints:
- POST /api/check          → headline or URL verification
- POST /api/check-url      → explicit URL analysis
- POST /api/check-image    → image upload + OCR + verify
- POST /api/extract-claims → claim extraction only
- POST /api/explain        → LIME / SHAP
- POST /api/chat           → chatbot
- GET  /api/live-feed
- GET  /api/history
- DELETE /api/history/<id>
- GET  /api/stats

Run:
    python webapp/app.py
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

# Phase 2 + 3 modules (optional — degrade gracefully)
try:
    from src.article_fetcher import fetch_article, is_url
except ImportError:
    def fetch_article(url):
        return {"ok": False, "error": "article_fetcher not installed", "title": "", "text": ""}
    def is_url(text):
        t = (text or "").strip()
        return t.startswith("http://") or t.startswith("https://")

try:
    from src.language_utils import detect_language, translate_to_english, is_hindi_or_hinglish
except ImportError:
    def detect_language(text):
        return "en"
    def translate_to_english(text, source_lang=None):
        return {"ok": True, "translated": text, "source_lang": "en", "method": "passthrough"}
    def is_hindi_or_hinglish(text):
        return False

try:
    from src.claim_extractor import extract_claims
except ImportError:
    def extract_claims(text, max_claims=5):
        return {"ok": False, "claims": [], "error": "claim_extractor not installed"}

try:
    from src.image_ocr import extract_text_from_image, available_backends
except ImportError:
    def extract_text_from_image(image_bytes, prefer="auto"):
        return {"ok": False, "text": "", "error": "image_ocr not installed"}
    def available_backends():
        return []

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

def run_verification_pipeline(headline: str, extra: dict = None) -> dict:
    """
    Shared 5-layer verification used by /api/check, /api/check-url, /api/check-image.
    Returns the full Phase-1 response dict (verdict, layers, evidence, ...).
    """
    extra = extra or {}
    model_name, best_model = get_model()

    # Language handling (Phase 2)
    lang = detect_language(headline)
    ml_text = headline
    translation_info = None
    if lang not in ("en", "unknown"):
        tr = translate_to_english(headline, source_lang=lang)
        translation_info = tr
        if tr.get("ok") and tr.get("translated"):
            ml_text = tr["translated"]

    layers = {}
    evidence = []
    score_real = 0
    score_fake = 0

    # ---- LAYER 1 ----
    verification = verify_headline(headline)
    matched = verification.get("matched_sources", [])
    is_verified = bool(verification.get("verified"))

    layers["trusted_source"] = {
        "name": "Trusted Source",
        "status": "passed" if is_verified else "no_match",
        "detail": (
            f"Matched {len(matched)} trusted source(s)"
            if is_verified else "No matching trusted outlet found"
        ),
        "sources": [
            {
                "title": m.get("title", ""),
                "source": m.get("source", "Unknown"),
                "similarity": m.get("similarity"),
            }
            for m in matched
        ],
        "provider": verification.get("provider", "unknown"),
    }
    if is_verified:
        score_real += 3
        for m in matched:
            evidence.append({
                "label": f"Trusted: {m.get('source', 'Unknown')}",
                "detail": m.get("title", ""),
                "url": None,
                "type": "trusted_source",
            })

    # ---- LAYER 2 ----
    fc = search_fact_checks(headline)
    reviews = fc.get("reviews", []) if fc.get("found") else []
    fact_status = "not_configured"
    fact_verdict = None
    fact_detail = "Fact-check API key not configured"

    if fc.get("configured") is False:
        fact_status = "skipped"
        fact_detail = "Google Fact Check API key not set"
    elif fc.get("error"):
        fact_status = "error"
        fact_detail = "Fact-check API request failed"
    elif reviews:
        top = reviews[0]
        rating = str(top.get("rating", "")).strip()
        rating_lower = rating.lower()
        fake_words = ["false", "fake", "misleading", "pants", "incorrect", "not true", "mostly false"]
        real_words = ["true", "mostly true", "correct", "accurate"]
        if any(w in rating_lower for w in fake_words):
            fact_verdict = "FAKE"
            fact_status = "flagged_fake"
            score_fake += 3
        elif any(w in rating_lower for w in real_words):
            fact_verdict = "REAL"
            fact_status = "confirmed_real"
            score_real += 3
        else:
            fact_verdict = "MIXED"
            fact_status = "reviewed"
            score_fake += 1
        fact_detail = f"{top.get('publisher', 'Fact-checker')}: {rating}"
        evidence.append({
            "label": f"Fact-check: {top.get('publisher', 'Unknown')}",
            "detail": rating,
            "url": top.get("url") or None,
            "type": "fact_check",
        })
    else:
        fact_status = "no_review"
        fact_detail = "No existing fact-check found for this claim"

    layers["fact_check"] = {
        "name": "Fact Check",
        "status": fact_status,
        "detail": fact_detail,
        "verdict": fact_verdict,
        "reviews": [
            {
                "publisher": r.get("publisher"),
                "rating": r.get("rating"),
                "url": r.get("url"),
                "claim": r.get("claim"),
            }
            for r in reviews[:3]
        ],
    }

    # ---- LAYER 3 ----
    plausibility = check_plausibility(headline)
    flagged = bool(plausibility.get("flagged"))
    matched_patterns = plausibility.get("matched_patterns", [])
    layers["plausibility"] = {
        "name": "Plausibility / Red-flag",
        "status": "flagged" if flagged else "clean",
        "detail": (
            f"Matched patterns: {', '.join(matched_patterns[:4])}"
            if flagged else "No common fake-news red-flag patterns detected"
        ),
        "matched_patterns": matched_patterns,
    }
    if flagged:
        score_fake += 2
        evidence.append({
            "label": "Red-flag patterns",
            "detail": ", ".join(matched_patterns[:5]),
            "url": None,
            "type": "red_flag",
        })

    # ---- LAYER 4 ----
    llm_result = analyze_with_llm(headline)
    llm_available = bool(llm_result.get("available"))
    llm_verdict = llm_result.get("verdict")
    llm_reason = llm_result.get("reason", "")
    llm_provider = llm_result.get("provider")

    if not llm_available:
        llm_status = "skipped"
        llm_detail = llm_reason or "No LLM API key configured"
    elif llm_verdict == "IMPLAUSIBLE":
        llm_status = "flagged"
        llm_detail = llm_reason
        score_fake += 2
        evidence.append({
            "label": f"AI Reasoning ({llm_provider})",
            "detail": llm_reason,
            "url": None,
            "type": "llm",
        })
    else:
        llm_status = "plausible"
        llm_detail = llm_reason or "Claim appears plausible"
        score_real += 1

    layers["llm_reasoning"] = {
        "name": "AI Reasoning",
        "status": llm_status,
        "detail": llm_detail,
        "verdict": llm_verdict,
        "provider": llm_provider,
    }

    # ---- LAYER 5 (use English translation for ML if needed) ----
    model_result = predict_headlines([ml_text], best_model)[0]
    prediction = str(model_result.get("prediction", "UNVERIFIED")).upper()
    confidence = model_result.get("confidence")
    conf_val = confidence
    if conf_val is not None:
        try:
            conf_val = float(conf_val)
            if conf_val > 1.0:
                conf_val = conf_val / 100.0
        except (TypeError, ValueError):
            conf_val = None

    if prediction == "REAL":
        score_real += 1 if (conf_val is None or conf_val < 0.7) else 2
    elif prediction == "FAKE":
        score_fake += 1 if (conf_val is None or conf_val < 0.7) else 2

    layers["ml_model"] = {
        "name": "ML Prediction",
        "status": "completed",
        "detail": f"Model predicted {prediction}"
                  + (f" ({round(conf_val * 100, 1)}%)" if conf_val is not None else ""),
        "prediction": prediction,
        "confidence": conf_val,
        "model_used": model_name,
        "input_language": lang,
        "ml_input_was_translated": bool(translation_info and translation_info.get("ok") and lang != "en"),
    }

    # ---- Final 3-way verdict ----
    if score_real >= 3 and score_fake == 0:
        final_verdict, final_label, confidence_label = "Likely Real", "REAL", "High"
    elif score_fake >= 3 and score_real == 0:
        final_verdict, final_label, confidence_label = "Suspicious", "FAKE", "High"
    elif score_real > score_fake and score_real >= 2:
        final_verdict, final_label, confidence_label = "Likely Real", "REAL", "Medium"
    elif score_fake > score_real and score_fake >= 2:
        final_verdict, final_label, confidence_label = "Suspicious", "FAKE", "Medium"
    else:
        final_verdict, final_label, confidence_label = "Uncertain", "UNVERIFIED", "Low"

    if is_verified:
        mode = "verified"
    elif fact_status in ("flagged_fake", "confirmed_real"):
        mode = "fact_checked"
    elif flagged:
        mode = "flagged"
    elif llm_status == "flagged":
        mode = "llm_flagged"
    else:
        mode = "unverified"

    reason_parts = []
    if is_verified:
        reason_parts.append("Matched trusted news sources")
    if fact_status == "flagged_fake":
        reason_parts.append("Professional fact-checkers rated it false/misleading")
    elif fact_status == "confirmed_real":
        reason_parts.append("Professional fact-checkers rated it true")
    if flagged:
        reason_parts.append("Contains common fake-news red-flag patterns")
    if llm_status == "flagged":
        reason_parts.append("AI reasoning found the claim implausible")
    if not reason_parts:
        reason_parts.append(
            f"Model prediction: {prediction}"
            + (f" ({round(conf_val * 100, 1)}% confidence)" if conf_val else "")
        )
    reason = ". ".join(reason_parts) + "."

    log_check(headline, final_label, mode, reason[:500])

    result = {
        "headline": headline,
        "verdict": final_verdict,
        "verdict_label": final_label,
        "confidence_label": confidence_label,
        "mode": mode,
        "reason": reason,
        "score": {"real_signals": score_real, "fake_signals": score_fake},
        "layers": layers,
        "evidence": evidence,
        "model_used": model_name,
        "model_confidence": conf_val,
        "language": lang,
        "translation": translation_info,
    }
    result.update(extra)
    return result


@app.route(
    "/api/check",
    methods=["POST"]
)
def api_check():
    """
    Phase 1+2 checker:
    - Accepts headline OR news URL
    - Runs ALL 5 layers
    - 3-way verdict + layer report + evidence
    - Auto language detect + translate for ML
    """
    data = (
        request
        .get_json(
            force=True,
            silent=True
        )
        or {}
    )

    raw = str(
        data.get("headline") or data.get("text") or data.get("url") or ""
    ).strip()

    if not raw:
        return jsonify({"error": "Headline or URL is empty"}), 400

    try:
        # Phase-2: if input looks like a URL → fetch full article
        if is_url(raw) or data.get("url"):
            url = data.get("url") or raw
            article = fetch_article(url)
            if not article.get("ok"):
                return jsonify({
                    "error": article.get("error") or "Could not fetch article",
                    "url": url,
                }), 422

            title = article.get("title") or ""
            body = article.get("text") or ""
            # Use title as primary claim; keep body for claim extraction
            headline = title if title else body[:280]
            extra = {
                "input_type": "url",
                "article": {
                    "url": url,
                    "title": title,
                    "word_count": article.get("word_count"),
                    "method": article.get("method"),
                    "text_preview": body[:500],
                },
            }
            # Optional claim extraction
            if data.get("extract_claims", True) and len(body) > 100:
                claims_res = extract_claims(body)
                extra["claims"] = claims_res.get("claims", [])
                extra["claims_method"] = claims_res.get("method")
                # Verify top claims too
                claim_results = []
                for c in (claims_res.get("claims") or [])[:3]:
                    try:
                        claim_results.append(run_verification_pipeline(c))
                    except Exception:
                        pass
                extra["claim_verdicts"] = claim_results

            result = run_verification_pipeline(headline, extra=extra)
            return jsonify(result)

        # Normal headline path
        result = run_verification_pipeline(raw, extra={"input_type": "headline"})
        return jsonify(result)

    except Exception as e:
        print("\n========== CHECK ERROR ==========")
        print(str(e))
        print("==================================\n")
        return jsonify({"error": f"Verification failed: {str(e)}"}), 500



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
# PHASE 2 — Explicit URL check
# ============================================================

@app.route("/api/check-url", methods=["POST"])
def api_check_url():
    data = request.get_json(force=True, silent=True) or {}
    url = str(data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "URL is required"}), 400
    # Auto-add https:// if missing
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url

    try:
        article = fetch_article(url)
        if not article.get("ok"):
            return jsonify({
                "error": article.get("error") or "Fetch failed",
                "url": url,
                "hint": "Try a public news article URL. Paywalled or JS-only pages may fail.",
            }), 422

        title = article.get("title") or ""
        body = article.get("text") or ""
        headline = title if title else body[:280]

        extra = {
            "input_type": "url",
            "article": {
                "url": url,
                "title": title,
                "word_count": article.get("word_count"),
                "method": article.get("method"),
                "text_preview": body[:600],
            },
        }

        if data.get("extract_claims", True) and len(body) > 80:
            claims_res = extract_claims(body)
            extra["claims"] = claims_res.get("claims", [])
            extra["claims_method"] = claims_res.get("method")
            claim_results = []
            for c in (claims_res.get("claims") or [])[:3]:
                try:
                    claim_results.append(run_verification_pipeline(c))
                except Exception:
                    pass
            extra["claim_verdicts"] = claim_results

        result = run_verification_pipeline(headline, extra=extra)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# PHASE 3 — Claim extraction only
# ============================================================

@app.route("/api/extract-claims", methods=["POST"])
def api_extract_claims():
    data = request.get_json(force=True, silent=True) or {}
    text = str(data.get("text") or data.get("article") or "").strip()
    if not text:
        return jsonify({"error": "Text is required"}), 400
    try:
        result = extract_claims(text, max_claims=int(data.get("max_claims", 5)))
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "claims": [], "error": str(e)}), 500


# ============================================================
# PHASE 3 — Image OCR + verification
# ============================================================

@app.route("/api/check-image", methods=["POST"])
def api_check_image():
    """
    Accept multipart image upload OR JSON with base64.
    OCR → extract text → run verification pipeline.
    """
    try:
        image_bytes = None

        if request.files:
            f = request.files.get("image") or request.files.get("file")
            if f:
                image_bytes = f.read()
        else:
            data = request.get_json(force=True, silent=True) or {}
            b64 = data.get("image_base64") or data.get("base64")
            if b64:
                import base64
                if "," in b64:
                    b64 = b64.split(",", 1)[1]
                image_bytes = base64.b64decode(b64)

        if not image_bytes:
            return jsonify({
                "error": "No image provided. Send multipart 'image' or JSON image_base64."
            }), 400

        ocr = extract_text_from_image(image_bytes)
        if not ocr.get("ok") or not (ocr.get("text") or "").strip():
            return jsonify({
                "error": ocr.get("error") or "OCR failed / no text found in image",
                "ocr": ocr,
                "backends": available_backends(),
                "hint": "Add Aptfile (tesseract-ocr) to repo root and redeploy. Or use Headline / URL tab.",
            }), 422

        text = ocr["text"]
        lines = [ln.strip() for ln in text.splitlines() if len(ln.strip()) > 20]
        headline = lines[0] if lines else text[:280]

        extra = {
            "input_type": "image",
            "ocr": {
                "method": ocr.get("method"),
                "char_count": ocr.get("char_count"),
                "full_text": text[:1500],
            },
        }

        if len(text) > 80:
            claims_res = extract_claims(text)
            extra["claims"] = claims_res.get("claims", [])
            extra["claims_method"] = claims_res.get("method")

        result = run_verification_pipeline(headline, extra=extra)
        return jsonify(result)

    except Exception as e:
        print("IMAGE CHECK ERROR:", e)
        return jsonify({"error": str(e)}), 500


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