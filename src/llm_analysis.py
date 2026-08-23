"""
LLM reasoning layer — uses an LLM to judge a headline's plausibility using
general world knowledge, when live verification, fact-check lookup, and the
rule-based plausibility check are all inconclusive. This catches implausible
claims that don't match any hardcoded regex pattern.

Supports two providers, tried in this order:
  1. Google Gemini (GEMINI_API_KEY) — free tier: https://aistudio.google.com/apikey
  2. Anthropic Claude (ANTHROPIC_API_KEY) — paid after free trial credits: https://console.anthropic.com

Whichever key is set first is used. If neither is configured, this layer is
skipped automatically — nothing breaks.
"""
import os
import json
import re
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

PROMPT_TEMPLATE = """You are a fact-plausibility checker. Given a news headline, judge only
whether it is PLAUSIBLE (could realistically be true, regardless of whether you've heard of
it) or IMPLAUSIBLE (describes something that could not realistically happen, e.g. sweeping
overnight policy changes, physically impossible events, absurd claims).

Respond ONLY with JSON, no other text: {{"verdict": "PLAUSIBLE" or "IMPLAUSIBLE", "reason": "<one short sentence>"}}

Headline: "{headline}\""""


def _extract_json(text):
    """LLMs sometimes wrap JSON in markdown fences or extra text -- pull out the object."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return json.loads(match.group(0) if match else text)


def _analyze_with_gemini(headline):
    resp = requests.post(
        GEMINI_URL,
        json={"contents": [{"parts": [{"text": PROMPT_TEMPLATE.format(headline=headline)}]}]},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    parsed = _extract_json(text)
    return {"available": True, "verdict": parsed.get("verdict"), "reason": parsed.get("reason", ""), "provider": "gemini"}


def _analyze_with_claude(headline):
    resp = requests.post(
        ANTHROPIC_URL,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 150,
            "messages": [{"role": "user", "content": PROMPT_TEMPLATE.format(headline=headline)}],
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    text = data["content"][0]["text"].strip()
    parsed = _extract_json(text)
    return {"available": True, "verdict": parsed.get("verdict"), "reason": parsed.get("reason", ""), "provider": "claude"}


def analyze_with_llm(headline):
    """
    Ask an LLM to judge whether a headline is plausible. Tries Gemini (free) first,
    then Claude, depending on which API key is configured.

    Returns: {"available": bool, "verdict": "PLAUSIBLE"|"IMPLAUSIBLE"|None, "reason": str, "provider": str}
    """
    if GEMINI_API_KEY:
        try:
            return _analyze_with_gemini(headline)
        except Exception:
            pass  # fall through to Claude if configured

    if ANTHROPIC_API_KEY:
        try:
            return _analyze_with_claude(headline)
        except Exception as e:
            return {"available": False, "verdict": None, "reason": f"LLM call failed: {e}", "provider": None}

    return {"available": False, "verdict": None, "reason": "No GEMINI_API_KEY or ANTHROPIC_API_KEY configured", "provider": None}
