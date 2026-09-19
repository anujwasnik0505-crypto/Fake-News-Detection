"""
Phase-3: Claim extraction from full article text.

Uses the same LLM providers already configured in llm_analysis.py
to pull out 2-6 short factual claims that can be verified independently.
"""

from __future__ import annotations

import json
import os
import re

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()

CLAIM_PROMPT = """You are a fact-checking assistant.
Extract the main factual claims from the news text below.

Rules:
- Return 2 to 6 short, self-contained factual claims.
- Each claim should be one sentence that can be verified as true or false.
- Ignore opinions, speculation, and rhetorical language.
- Prefer concrete claims (who did what, when, where, numbers).
- Respond ONLY with valid JSON in this exact format:

{{
  "claims": [
    "Claim one sentence.",
    "Claim two sentence."
  ]
}}

Text:
\"\"\"
{text}
\"\"\"
"""


def _extract_json(text: str) -> dict:
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found")
    return json.loads(match.group(0))


def _gemini_claims(text: str) -> list:
    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/gemini-2.0-flash:generateContent"
    )
    resp = requests.post(
        url,
        params={"key": GEMINI_API_KEY},
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": CLAIM_PROMPT.format(text=text[:6000])}]}],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
                "maxOutputTokens": 800,
            },
        },
        timeout=25,
    )
    resp.raise_for_status()
    data = resp.json()
    raw = data["candidates"][0]["content"]["parts"][0]["text"]
    parsed = _extract_json(raw)
    claims = parsed.get("claims") or []
    return [c.strip() for c in claims if isinstance(c, str) and len(c.strip()) > 15]


def _groq_claims(text: str) -> list:
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "Return only valid JSON."},
                {"role": "user", "content": CLAIM_PROMPT.format(text=text[:6000])},
            ],
            "temperature": 0.1,
            "max_tokens": 800,
        },
        timeout=25,
    )
    resp.raise_for_status()
    data = resp.json()
    raw = data["choices"][0]["message"]["content"]
    parsed = _extract_json(raw)
    claims = parsed.get("claims") or []
    return [c.strip() for c in claims if isinstance(c, str) and len(c.strip()) > 15]


def _heuristic_claims(text: str, max_claims: int = 4) -> list:
    """Fallback when no LLM is available: split into sentences and keep longer ones."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    claims = []
    for s in sentences:
        s = s.strip()
        if 40 < len(s) < 220:
            # Prefer sentences that look factual
            if re.search(r"\b(said|announced|confirmed|reported|according|will|has|have|was|were)\b", s, re.I):
                claims.append(s)
            elif len(claims) < 2:
                claims.append(s)
        if len(claims) >= max_claims:
            break
    return claims


def extract_claims(text: str, max_claims: int = 5) -> dict:
    """
    Extract factual claims from article / long text.

    Returns:
    {
        "ok": bool,
        "claims": [str, ...],
        "method": "gemini" | "groq" | "heuristic" | None,
        "error": str,
    }
    """
    text = (text or "").strip()
    if not text or len(text) < 40:
        return {"ok": False, "claims": [], "method": None,
                "error": "Text too short for claim extraction"}

    # Prefer Gemini → Groq → heuristic
    if GEMINI_API_KEY:
        try:
            claims = _gemini_claims(text)[:max_claims]
            if claims:
                return {"ok": True, "claims": claims, "method": "gemini", "error": None}
        except Exception as e:
            last_err = str(e)
    else:
        last_err = None

    if GROQ_API_KEY:
        try:
            claims = _groq_claims(text)[:max_claims]
            if claims:
                return {"ok": True, "claims": claims, "method": "groq", "error": None}
        except Exception as e:
            last_err = str(e)

    claims = _heuristic_claims(text, max_claims=max_claims)
    if claims:
        return {
            "ok": True,
            "claims": claims,
            "method": "heuristic",
            "error": last_err,
        }

    return {
        "ok": False,
        "claims": [],
        "method": None,
        "error": last_err or "Could not extract claims",
    }
