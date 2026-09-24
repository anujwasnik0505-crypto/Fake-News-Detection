"""
Multi-provider LLM reasoning layer for Fake News Detection.

Now returns FULL analysis of the headline:
- What the claim is saying
- Key points
- Detailed plausibility reasoning
- Confidence
- Clear PLAUSIBLE / IMPLAUSIBLE verdict

Provider priority: Gemini → Groq → Mistral → OpenRouter → Cohere → Claude
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


# ============================================================
# API KEYS
# ============================================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "").strip()
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
COHERE_API_KEY = os.environ.get("COHERE_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()


# ============================================================
# ENDPOINTS & MODELS
# ============================================================

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


# ============================================================
# FULL ANALYSIS PROMPT
# ============================================================

PROMPT_TEMPLATE = """You are an expert news analyst working inside a fake-news detection system.

Analyse the given news headline COMPLETELY and carefully.

Your tasks:
1. Understand what the headline is actually saying (full meaning).
2. Extract the main claim / topic in simple words.
3. List 2-4 key points present in the headline.
4. Decide if the claim is PLAUSIBLE or IMPLAUSIBLE in the real world.
5. Give a clear, detailed reason for your decision.
6. Give a confidence score (0 to 100).

STRICT RULES for verdict:
- PLAUSIBLE = the topic could realistically happen (politics, trade, tariffs, economy, diplomacy, science, crime, sports, etc.).
- IMPLAUSIBLE = only if the claim is physically impossible, supernatural, or extremely absurd.
- Normal news about tariffs, trade deals, India-US relations, questions like "Can X reduce Y?" → almost always PLAUSIBLE.
- Do NOT mark IMPLAUSIBLE just because the news is dramatic, controversial, or uses high numbers (e.g. 100% tariff).
- When in doubt → choose PLAUSIBLE.
- Be accurate and specific to THIS headline.

Respond ONLY with valid JSON in exactly this format (no markdown, no extra text):

{{
  "verdict": "PLAUSIBLE",
  "confidence": 85,
  "summary": "One or two sentences explaining what the headline is talking about.",
  "main_claim": "The core factual claim in simple words.",
  "key_points": [
    "Point 1",
    "Point 2",
    "Point 3"
  ],
  "reason": "Detailed 2-4 sentence explanation of why this is plausible or implausible, referring to real-world knowledge."
}}

Headline:
"{headline}"
"""


# ============================================================
# JSON PARSER
# ============================================================

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

    # Normalize fields
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

    return {
        "verdict": verdict,
        "confidence": confidence,
        "summary": str(parsed.get("summary", "")).strip(),
        "main_claim": str(parsed.get("main_claim", "")).strip(),
        "key_points": key_points,
        "reason": str(parsed.get("reason", "")).strip(),
    }


def _clean_headline(headline: str) -> str:
    h = (headline or "").strip()
    h = re.sub(r"^\[(?:tesseract|gemini-vision|easyocr|gemini)\]\s*", "", h, flags=re.I)
    h = re.sub(r"\s+", " ", h).strip()
    return h


# ============================================================
# PROVIDERS
# ============================================================

def _analyze_with_gemini(headline: str) -> dict:
    resp = requests.post(
        GEMINI_URL,
        params={"key": GEMINI_API_KEY},
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": PROMPT_TEMPLATE.format(headline=headline)}]}],
            "generationConfig": {
                "temperature": 0.15,
                "responseMimeType": "application/json",
                "maxOutputTokens": 600,
            },
        },
        timeout=30,
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
                        "You are an expert news analyst. "
                        "Give a full, accurate analysis of the headline. "
                        "Mark IMPLAUSIBLE only for absurd/impossible claims. "
                        "Normal political, trade, tariff, economic headlines are PLAUSIBLE. "
                        "Return only valid JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": PROMPT_TEMPLATE.format(headline=headline),
                },
            ],
            "temperature": 0.15,
            "max_tokens": 600,
        },
        timeout=30,
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
                    "content": "You are an expert news analyst. Return only valid JSON with full analysis.",
                },
                {
                    "role": "user",
                    "content": PROMPT_TEMPLATE.format(headline=headline),
                },
            ],
            "temperature": 0.15,
            "max_tokens": 600,
        },
        timeout=30,
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
            "max_tokens": 600,
            "messages": [
                {
                    "role": "user",
                    "content": PROMPT_TEMPLATE.format(headline=headline),
                }
            ],
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    text = data["content"][0]["text"]
    parsed = _extract_json(text)
    return {**parsed, "available": True, "provider": "claude"}


# ============================================================
# MAIN FUNCTION
# ============================================================

def analyze_with_llm(headline: str) -> dict:
    """
    Full headline analysis.

    Returns:
    {
        "available": bool,
        "verdict": "PLAUSIBLE" | "IMPLAUSIBLE" | None,
        "confidence": int (0-100),
        "summary": str,
        "main_claim": str,
        "key_points": [str, ...],
        "reason": str,          # detailed explanation
        "provider": str | None
    }
    """
    headline = _clean_headline(headline)

    if not headline or len(headline) < 10:
        return {
            "available": False,
            "verdict": None,
            "confidence": 0,
            "summary": "",
            "main_claim": "",
            "key_points": [],
            "reason": "Headline too short for analysis",
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
        "provider": None,
    }
