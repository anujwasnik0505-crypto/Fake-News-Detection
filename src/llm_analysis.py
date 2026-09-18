"""
Multi-provider LLM reasoning layer for Fake News Detection.

Provider priority:
1. Google Gemini
2. Groq
3. Mistral
4. OpenRouter
5. Cohere
6. Anthropic Claude

The first configured/working provider is used.
If all providers fail or no key is configured, the layer is skipped.
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
# API ENDPOINTS
# ============================================================

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/gemini-3.8-flash:generateContent"
)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

COHERE_URL = "https://api.cohere.com/v2/chat"

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


# ============================================================
# MODELS
# ============================================================

GROQ_MODEL = "llama-3.3-70b-versatile"
MISTRAL_MODEL = "mistral-small-latest"

# OpenRouter model can be changed without changing the code.
OPENROUTER_MODEL = os.environ.get(
    "OPENROUTER_MODEL",
    "openai/gpt-oss-120b"
)

COHERE_MODEL = "command-a-plus-05-2026"

ANTHROPIC_MODEL = "claude-sonnet-4-6"


# ============================================================
# PROMPT
# ============================================================

PROMPT_TEMPLATE = """You are a fact-plausibility checker for a fake-news detection system.

Given a news headline, judge ONLY whether the claim is realistically plausible.

IMPORTANT:
- Do NOT decide whether the headline is actually true just because it sounds plausible.
- You are checking plausibility, not performing live fact verification.
- PLAUSIBLE means the event/claim could realistically happen.
- IMPLAUSIBLE means the claim describes something that is physically impossible,
  absurd, or extremely unrealistic.
- Do not use political preference or ideology.
- Keep the explanation short.

Respond ONLY with valid JSON in exactly this format:

{{
  "verdict": "PLAUSIBLE" or "IMPLAUSIBLE",
  "reason": "one short sentence"
}}

Headline:
"{headline}"
"""


# ============================================================
# JSON PARSER
# ============================================================

def _extract_json(text):
    """
    Extract JSON even if the LLM accidentally adds markdown fences
    or extra text.
    """
    if not text:
        raise ValueError("Empty LLM response")

    text = text.strip()

    # Remove markdown code fences
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    match = re.search(r"\{.*\}", text, re.DOTALL)

    if not match:
        raise ValueError(f"No JSON object found in response: {text}")

    parsed = json.loads(match.group(0))

    verdict = str(parsed.get("verdict", "")).upper().strip()

    if verdict not in {"PLAUSIBLE", "IMPLAUSIBLE"}:
        raise ValueError(f"Invalid verdict returned: {verdict}")

    return {
        "verdict": verdict,
        "reason": str(parsed.get("reason", "")).strip(),
    }


# ============================================================
# GEMINI
# ============================================================

def _analyze_with_gemini(headline):

    resp = requests.post(
        GEMINI_URL,
        params={"key": GEMINI_API_KEY},
        headers={
            "Content-Type": "application/json",
        },
        json={
            "contents": [
                {
                    "parts": [
                        {
                            "text": PROMPT_TEMPLATE.format(
                                headline=headline
                            )
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        },
        timeout=20,
    )

    resp.raise_for_status()

    data = resp.json()

    text = data["candidates"][0]["content"]["parts"][0]["text"]

    parsed = _extract_json(text)

    return {
        "available": True,
        "verdict": parsed["verdict"],
        "reason": parsed["reason"],
        "provider": "gemini",
    }


# ============================================================
# OPENAI-COMPATIBLE PROVIDERS
# ============================================================

def _openai_style_request(
    url,
    api_key,
    model,
    headline,
    provider,
    extra_headers=None,
):
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
                        "You are a strict fact-plausibility checker. "
                        "Return only valid JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": PROMPT_TEMPLATE.format(
                        headline=headline
                    ),
                },
            ],
            "temperature": 0.1,
            "max_tokens": 150,
        },
        timeout=20,
    )

    resp.raise_for_status()

    data = resp.json()

    text = data["choices"][0]["message"]["content"]

    parsed = _extract_json(text)

    return {
        "available": True,
        "verdict": parsed["verdict"],
        "reason": parsed["reason"],
        "provider": provider,
    }


# ============================================================
# GROQ
# ============================================================

def _analyze_with_groq(headline):

    return _openai_style_request(
        url=GROQ_URL,
        api_key=GROQ_API_KEY,
        model=GROQ_MODEL,
        headline=headline,
        provider="groq",
    )


# ============================================================
# MISTRAL
# ============================================================

def _analyze_with_mistral(headline):

    return _openai_style_request(
        url=MISTRAL_URL,
        api_key=MISTRAL_API_KEY,
        model=MISTRAL_MODEL,
        headline=headline,
        provider="mistral",
    )


# ============================================================
# OPENROUTER
# ============================================================

def _analyze_with_openrouter(headline):

    return _openai_style_request(
        url=OPENROUTER_URL,
        api_key=OPENROUTER_API_KEY,
        model=OPENROUTER_MODEL,
        headline=headline,
        provider="openrouter",
        extra_headers={
            "HTTP-Referer": "https://github.com/anujwasnik0505-crypto/Fake-News-Detection",
            "X-Title": "Fake News Detection",
        },
    )


# ============================================================
# COHERE
# ============================================================

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
                    "content": (
                        "You are a strict fact-plausibility checker. "
                        "Return only valid JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": PROMPT_TEMPLATE.format(
                        headline=headline
                    ),
                },
            ],
            "temperature": 0.1,
            "max_tokens": 150,
        },
        timeout=20,
    )

    resp.raise_for_status()

    data = resp.json()

    text = data["message"]["content"][0]["text"]

    parsed = _extract_json(text)

    return {
        "available": True,
        "verdict": parsed["verdict"],
        "reason": parsed["reason"],
        "provider": "cohere",
    }


# ============================================================
# ANTHROPIC CLAUDE
# ============================================================

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
            "max_tokens": 150,
            "messages": [
                {
                    "role": "user",
                    "content": PROMPT_TEMPLATE.format(
                        headline=headline
                    ),
                }
            ],
        },
        timeout=20,
    )

    resp.raise_for_status()

    data = resp.json()

    text = data["content"][0]["text"]

    parsed = _extract_json(text)

    return {
        "available": True,
        "verdict": parsed["verdict"],
        "reason": parsed["reason"],
        "provider": "claude",
    }


# ============================================================
# MAIN LLM FUNCTION
# ============================================================

def analyze_with_llm(headline):
    """
    Try all configured LLM providers in priority order.

    Returns:

    {
        "available": bool,
        "verdict": "PLAUSIBLE" | "IMPLAUSIBLE" | None,
        "reason": str,
        "provider": str | None
    }

    Provider order:
        Gemini
        Groq
        Mistral
        OpenRouter
        Cohere
        Claude
    """

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

            if result.get("verdict") in {
                "PLAUSIBLE",
                "IMPLAUSIBLE",
            }:
                return result

        except Exception as e:
            errors.append(f"{name}: {str(e)}")

    # No API keys
    if not configured:
        return {
            "available": False,
            "verdict": None,
            "reason": (
                "No LLM API key configured. "
                "Set GEMINI_API_KEY, GROQ_API_KEY, MISTRAL_API_KEY, "
                "OPENROUTER_API_KEY, COHERE_API_KEY, or ANTHROPIC_API_KEY."
            ),
            "provider": None,
        }

    # All configured providers failed
    return {
        "available": False,
        "verdict": None,
        "reason": (
            "All configured LLM providers failed. "
            + " | ".join(errors)
        ),
        "provider": None,
    }