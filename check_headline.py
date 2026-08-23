"""
Manually check any headline you type — REAL or FAKE.

Four-layer approach:
1. Live-search trusted news outlets (NewsAPI.org, or free Google News RSS as
   fallback) to see if the headline is currently being reported.
2. Check Google Fact Check Tools API — has this claim already been reviewed
   by professional fact-checkers? (only runs if GOOGLE_FACTCHECK_API_KEY is set)
3. Rule-based implausibility check for common fake-news red flags.
4. LLM reasoning (Claude API) for plausibility judgment using world knowledge
   (only runs if ANTHROPIC_API_KEY is set).
5. Final fallback: the trained ML/DL model's prediction (style-based).

Every check is logged to a local SQLite database (history.db).

Usage:
    python check_headline.py
    python check_headline.py --text "Some headline here"
    python check_headline.py --history
"""
import argparse
import json
import os

from src.utils import MODELS_DIR, OUTPUT_DIR
from src.realtime_news import load_best_model, predict_headlines
from src.verify_news import verify_headline
from src.plausibility_check import check_plausibility
from src.factcheck import search_fact_checks
from src.llm_analysis import analyze_with_llm
from src.database import log_check, get_history


def get_best_model_name():
    with open(os.path.join(OUTPUT_DIR, "best_model.json")) as f:
        return json.load(f)["best_model"]


def hybrid_check(text, best_model):
    print(f"\nHeadline: {text}")
    print("Checking trusted news sources ...")
    verification = verify_headline(text)

    if verification.get("verified"):
        sources = ", ".join(m["source"] for m in verification["matched_sources"])
        print(f"\nREAL — Verified: currently reported by {sources}\n")
        log_check(text, "REAL", "verified", f"sources: {sources}")
        return

    # Layer 2: professional fact-checkers
    fc = search_fact_checks(text)
    if fc.get("found"):
        top = fc["reviews"][0]
        print(f"\nFlagged by fact-checkers: {top['publisher']} rated this \"{top['rating']}\"")
        verdict = "FAKE" if any(w in top["rating"].lower() for w in ["false", "fake", "misleading", "pants"]) else "REAL"
        print(f"Verdict: {verdict} (fact-check database match)\n")
        log_check(text, verdict, "fact_checked", f"{top['publisher']}: {top['rating']}")
        return

    # Layer 3: rule-based red flags
    plausibility = check_plausibility(text)
    if plausibility["flagged"]:
        print(f"\nNot found on trusted sources or fact-check databases, and matches "
              f"common fake-news patterns (sweeping/absolute claims, etc.)")
        print(f"Verdict: FAKE (flagged by pattern check)\n")
        log_check(text, "FAKE", "flagged", "matched implausibility patterns")
        return

    # Layer 4: LLM plausibility reasoning (only if configured)
    llm_result = analyze_with_llm(text)
    if llm_result["available"] and llm_result["verdict"] == "IMPLAUSIBLE":
        print(f"\nLLM plausibility check: IMPLAUSIBLE — {llm_result['reason']}")
        print(f"Verdict: FAKE (LLM reasoning)\n")
        log_check(text, "FAKE", "llm_flagged", llm_result["reason"])
        return

    # Layer 5: trained model fallback
    model_result = predict_headlines([text], best_model)[0]
    print(f"\nNo red flags detected by any check.")
    print(f"Model prediction (unverified, based on writing style): "
          f"{model_result['prediction']}  (confidence: {model_result['confidence']})\n")
    log_check(text, model_result["prediction"], "unverified", f"confidence: {model_result['confidence']}")


def show_history(limit=20):
    rows = get_history(limit)
    if not rows:
        print("No checks logged yet.")
        return
    print(f"\n--- Last {len(rows)} checks ---")
    for r in rows:
        print(f"[{r['checked_at']}] {r['verdict']:4s} ({r['mode']:10s}) {r['headline'][:70]}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", default=None, help="Headline to check (skips interactive mode)")
    parser.add_argument("--history", action="store_true", help="Show recent check history and exit")
    args = parser.parse_args()

    if args.history:
        show_history()
        return

    best_model_name = get_best_model_name()
    best_model = load_best_model(best_model_name, MODELS_DIR)
    print(f"Using model (final fallback): {best_model_name}")

    if args.text:
        hybrid_check(args.text, best_model)
        return

    print("Type a news headline and press Enter (type 'exit' to quit, 'history' to view past checks):\n")
    while True:
        text = input("> ").strip()
        if text.lower() in ("exit", "quit"):
            break
        if text.lower() == "history":
            show_history()
            continue
        if not text:
            continue
        hybrid_check(text, best_model)


if __name__ == "__main__":
    main()
