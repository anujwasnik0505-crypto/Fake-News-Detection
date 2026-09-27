"""
Multi-provider LLM reasoning layer for Fake News Detection.

ChatGPT-style detailed analysis + clear PLAUSIBLE / IMPLAUSIBLE for the pipeline.

Provider priority: Gemini → Groq → Mistral → OpenRouter → Cohere → Claude
"""

from __future__ import annotations

import os
import json
import re
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "").strip()
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
COHERE_API_KEY = os.environ.get("COHERE_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/gemini-2.0-flash:generateContent"
)
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
COHERE_URL = "https://api.cohere.com/v2/chat"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

GROQ_MODEL = "llama-3.3-70b-versatile"
MISTRAL_MODEL = "mistral-small-latest"
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
COHERE_MODEL = "command-r-plus"
ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"


PROMPT_TEMPLATE = """You are a helpful news analyst (like ChatGPT) inside a fake-news detection app.

The user gave this text (it may be 2–3 words, a headline, or a full paragraph):
"{headline}"

Write a clear, natural, ChatGPT-style analysis in simple language (English is fine; you may use simple Hindi words if the input is Hindi).

You MUST:
1. Explain what the claim/text is saying.
2. Say whether it is likely REAL-world plausible or not.
3. Cover historical facts correctly:
   - Widely known true history (e.g. "Mahatma Gandhi died", "India got independence in 1947") → treat as PLAUSIBLE / real fact.
   - Do NOT mark real history as fake just because it is not in today's news.
4. For normal politics, trade, science, sports news → usually PLAUSIBLE.
5. Only mark IMPLAUSIBLE for absurd / impossible / clearly fabricated-sounding claims.
6. Give a confidence from 0 to 100.
7. End with a short plain-language verdict line.

Also fill the JSON fields exactly (machine-readable).

Respond with ONLY valid JSON in this exact shape (no markdown fences):

{{
  "verdict": "PLAUSIBLE",
  "confidence": 85,
  "summary": "One or two sentences: what is this claim about?",
  "main_claim": "Core claim in simple words",
  "key_points": ["point 1", "point 2", "point 3"],
  "reason": "2-4 sentences of careful reasoning",
  "detailed_answer": "Write 1-3 short paragraphs here like ChatGPT would: friendly, clear, explain context, why real or suspicious, and any caveat (e.g. old historical fact vs breaking news). This is what the user will read."
}}

Rules for verdict:
- PLAUSIBLE = could be true / is a known fact / normal news topic
- IMPLAUSIBLE = absurd, impossible, or classic fake-news style fantasy
- When unsure but not absurd → PLAUSIBLE
"""


def _extract_json(text: str) -> dict:
    if not text:
        raise ValueError("Empty LLM response")
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found: {text[:250]}")
    parsed = json.loads(match.group(0))
    verdict = str(parsed.get("verdict", "")).upper().strip()
    if verdict not in {"PLAUSIBLE", "IMPLAUSIBLE"}:
        raise ValueError(f"Invalid verdict: {verdict}")

    confidence = parsed.get("confidence", 70)
    try:
        confidence = int(float(confidence))
        confidence = max(0, min(100, confidence))
    except (TypeError, ValueError):
        confidence = 70

    key_points = parsed.get("key_points") or []
    if not isinstance(key_points, list):
        key_points = [str(key_points)]
    key_points = [str(p).strip() for p in key_points if str(p).strip()][:6]

    detailed = str(parsed.get("detailed_answer") or parsed.get("reason") or "").strip()
    reason = str(parsed.get("reason") or "").strip()
    if not reason and detailed:
        reason = detailed[:400]

    return {
        "verdict": verdict,
        "confidence": confidence,
        "summary": str(parsed.get("summary", "")).strip(),
        "main_claim": str(parsed.get("main_claim", "")).strip(),
        "key_points": key_points,
        "reason": reason,
        "detailed_answer": detailed,
    }


def _clean_headline(headline: str) -> str:
    h = (headline or "").strip()
    h = re.sub(r"^\[(?:tesseract|gemini-vision|easyocr|gemini)\]\s*", "", h, flags=re.I)
    h = re.sub(r"\s+", " ", h).strip()
    return h


def _analyze_with_gemini(headline: str) -> dict:
    resp = requests.post(
        GEMINI_URL,
        params={"key": GEMINI_API_KEY},
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": PROMPT_TEMPLATE.format(headline=headline)}]}],
            "generationConfig": {
                "temperature": 0.25,
                "responseMimeType": "application/json",
                "maxOutputTokens": 900,
            },
        },
        timeout=35,
    )
    resp.raise_for_status()
    data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    parsed = _extract_json(text)
    return {**parsed, "available": True, "provider": "gemini"}


def _openai_style_request(url, api_key, model, headline, provider, extra_headers=None):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)

    resp = requests.post(
        url,
        headers=headers,
        json={
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful news analyst like ChatGPT. "
                        "Give a clear detailed_answer for humans, and valid JSON fields. "
                        "Known historical facts (e.g. Gandhi died in 1948) are PLAUSIBLE. "
                        "Only mark IMPLAUSIBLE for absurd claims. Return only valid JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": PROMPT_TEMPLATE.format(headline=headline),
                },
            ],
            "temperature": 0.25,
            "max_tokens": 900,
        },
        timeout=35,
    )
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    parsed = _extract_json(text)
    return {**parsed, "available": True, "provider": provider}


def _analyze_with_groq(headline):
    return _openai_style_request(GROQ_URL, GROQ_API_KEY, GROQ_MODEL, headline, "groq")


def _analyze_with_mistral(headline):
    return _openai_style_request(MISTRAL_URL, MISTRAL_API_KEY, MISTRAL_MODEL, headline, "mistral")


def _analyze_with_openrouter(headline):
    return _openai_style_request(
        OPENROUTER_URL,
        OPENROUTER_API_KEY,
        OPENROUTER_MODEL,
        headline,
        "openrouter",
        extra_headers={
            "HTTP-Referer": "https://github.com/anujwasnik0505-crypto/Fake-News-Detection",
            "X-Title": "Fake News Detection",
        },
    )


def _analyze_with_cohere(headline):
    resp = requests.post(
        COHERE_URL,
        headers={
            "Authorization": f"Bearer {COHERE_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": COHERE_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful news analyst like ChatGPT. Return only valid JSON.",
                },
                {
                    "role": "user",
                    "content": PROMPT_TEMPLATE.format(headline=headline),
                },
            ],
            "temperature": 0.25,
            "max_tokens": 900,
        },
        timeout=35,
    )
    resp.raise_for_status()
    data = resp.json()
    text = data["message"]["content"][0]["text"]
    parsed = _extract_json(text)
    return {**parsed, "available": True, "provider": "cohere"}


def _analyze_with_claude(headline):
    resp = requests.post(
        ANTHROPIC_URL,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": ANTHROPIC_MODEL,
            "max_tokens": 900,
            "messages": [
                {
                    "role": "user",
                    "content": PROMPT_TEMPLATE.format(headline=headline),
                }
            ],
        },
        timeout=35,
    )
    resp.raise_for_status()
    data = resp.json()
    text = data["content"][0]["text"]
    parsed = _extract_json(text)
    return {**parsed, "available": True, "provider": "claude"}


def analyze_with_llm(headline: str) -> dict:
    """
    ChatGPT-style analysis + pipeline fields.

    Returns:
    {
        available, verdict, confidence, summary, main_claim,
        key_points, reason, detailed_answer, provider
    }
    """
    headline = _clean_headline(headline)

    if not headline or len(headline) < 3:
        return {
            "available": False,
            "verdict": None,
            "confidence": 0,
            "summary": "",
            "main_claim": "",
            "key_points": [],
            "reason": "Text too short for analysis",
            "detailed_answer": "",
            "provider": None,
        }

    providers = [
        ("gemini", GEMINI_API_KEY, _analyze_with_gemini),
        ("groq", GROQ_API_KEY, _analyze_with_groq),
        ("mistral", MISTRAL_API_KEY, _analyze_with_mistral),
        ("openrouter", OPENROUTER_API_KEY, _analyze_with_openrouter),
        ("cohere", COHERE_API_KEY, _analyze_with_cohere),
        ("claude", ANTHROPIC_API_KEY, _analyze_with_claude),
    ]

    configured = False
    errors = []

    for name, api_key, analyzer in providers:
        if not api_key:
            continue
        configured = True
        try:
            result = analyzer(headline)
            if result.get("verdict") in {"PLAUSIBLE", "IMPLAUSIBLE"}:
                return result
        except Exception as e:
            errors.append(f"{name}: {str(e)[:120]}")

    if not configured:
        return {
            "available": False,
            "verdict": None,
            "confidence": 0,
            "summary": "",
            "main_claim": "",
            "key_points": [],
            "reason": "No LLM API key configured. Set GEMINI_API_KEY (free).",
            "detailed_answer": "",
            "provider": None,
        }

    return {
        "available": False,
        "verdict": None,
        "confidence": 0,
        "summary": "",
        "main_claim": "",
        "key_points": [],
        "reason": "All LLM providers failed. " + " | ".join(errors),
        "detailed_answer": "",
        "provider": None,
    }
