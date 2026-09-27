"""
AI Reasoning layer: Google/News search first, then ChatGPT-style REAL/FAKE analysis.

Uses free Google News RSS (no extra key). Snippets go into the LLM prompt
so the answer is grounded in search results, not only model memory.
"""

from __future__ import annotations

import os
import json
import re
from urllib.parse import quote

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False

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


def _clean_headline(headline: str) -> str:
    h = (headline or "").strip()
    h = re.sub(r"^\[(?:tesseract|gemini-vision|easyocr|gemini)\]\s*", "", h, flags=re.I)
    h = re.sub(r"\s+", " ", h).strip()
    return h


def search_web_for_claim(query: str, limit: int = 8) -> list:
    """
    Free web/news search via Google News RSS (ChatGPT-like grounding).
    Returns list of {title, source, link}.
    """
    query = _clean_headline(query)
    if not query or not HAS_FEEDPARSER:
        return []

    results = []
    try:
        url = (
            f"https://news.google.com/rss/search?q={quote(query)}"
            f"&hl=en-IN&gl=IN&ceid=IN:en"
        )
        feed = feedparser.parse(url)
        for entry in feed.entries[:limit]:
            title = entry.get("title") or ""
            source = ""
            if hasattr(entry, "source") and getattr(entry.source, "title", None):
                source = entry.source.title
            if not source and " - " in title:
                parts = title.rsplit(" - ", 1)
                if len(parts) == 2 and len(parts[1]) < 50:
                    title, source = parts[0].strip(), parts[1].strip()
            link = entry.get("link") or ""
            if title:
                results.append({
                    "title": title.strip(),
                    "source": source.strip() or "News",
                    "link": link,
                })
    except Exception:
        return results
    return results


def _format_search_block(results: list) -> str:
    if not results:
        return (
            "No relevant recent news results were found for this claim. "
            "Treat as unverified unless it is a well-known historical fact."
        )
    lines = []
    for i, r in enumerate(results[:8], 1):
        lines.append(f"{i}. [{r.get('source', 'News')}] {r.get('title', '')}")
    return "\n".join(lines)


PROMPT_TEMPLATE = """You are a helpful news analyst (like ChatGPT with web search).

User claim:
"{headline}"

Live search results from Google News (use these as evidence):
{search_block}

Write a clear ChatGPT-style analysis AND a machine verdict.

Rules:
1. Prefer the search results over pure guesses.
2. If reputable outlets report the same event → lean REAL / PLAUSIBLE.
3. If search shows debunks, "false", "rumour", "no evidence", or nothing supporting a breaking claim → lean FAKE / IMPLAUSIBLE or low confidence.
4. Known historical facts (e.g. Mahatma Gandhi died in 1948) → REAL even if not in today's feed.
5. Short political rumours with zero supporting news (e.g. "modi resigned" with no articles) → do NOT call REAL; mark IMPLAUSIBLE or uncertain tone in detailed_answer and verdict IMPLAUSIBLE if clearly unsupported rumour.
6. Be honest when evidence is weak.

Respond ONLY with valid JSON (no markdown):

{{
  "verdict": "PLAUSIBLE",
  "confidence": 75,
  "summary": "Brief what the claim is",
  "main_claim": "Core claim in simple words",
  "key_points": ["point1", "point2"],
  "reason": "2-4 sentences grounded in search results",
  "detailed_answer": "1-3 short paragraphs like ChatGPT: what you found on search, whether it looks real or fake/rumour, and advice to check trusted sources. Simple language."
}}

verdict must be exactly PLAUSIBLE or IMPLAUSIBLE.
- PLAUSIBLE = supported by search or known true fact
- IMPLAUSIBLE = unsupported rumour, debunked, or absurd
"""


def _extract_json(text: str) -> dict:
    if not text:
        raise ValueError("Empty LLM response")
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON: {text[:250]}")
    parsed = json.loads(match.group(0))
    verdict = str(parsed.get("verdict", "")).upper().strip()
    if verdict not in {"PLAUSIBLE", "IMPLAUSIBLE"}:
        raise ValueError(f"Invalid verdict: {verdict}")
    try:
        confidence = int(float(parsed.get("confidence", 70)))
        confidence = max(0, min(100, confidence))
    except (TypeError, ValueError):
        confidence = 70
    key_points = parsed.get("key_points") or []
    if not isinstance(key_points, list):
        key_points = [str(key_points)]
    key_points = [str(p).strip() for p in key_points if str(p).strip()][:6]
    detailed = str(parsed.get("detailed_answer") or parsed.get("reason") or "").strip()
    reason = str(parsed.get("reason") or "").strip() or detailed[:400]
    return {
        "verdict": verdict,
        "confidence": confidence,
        "summary": str(parsed.get("summary", "")).strip(),
        "main_claim": str(parsed.get("main_claim", "")).strip(),
        "key_points": key_points,
        "reason": reason,
        "detailed_answer": detailed,
    }


def _prompt(headline: str, search_block: str) -> str:
    return PROMPT_TEMPLATE.format(headline=headline, search_block=search_block)


def _analyze_with_gemini(headline: str, search_block: str) -> dict:
    resp = requests.post(
        GEMINI_URL,
        params={"key": GEMINI_API_KEY},
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": _prompt(headline, search_block)}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
                "maxOutputTokens": 1000,
            },
        },
        timeout=40,
    )
    resp.raise_for_status()
    data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return {**_extract_json(text), "available": True, "provider": "gemini"}


def _openai_style(url, api_key, model, headline, search_block, provider, extra_headers=None):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
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
                        "You are a news analyst with search results. "
                        "Ground your answer in the provided search snippets. "
                        "Unsupported political rumours are IMPLAUSIBLE. "
                        "Return only valid JSON."
                    ),
                },
                {"role": "user", "content": _prompt(headline, search_block)},
            ],
            "temperature": 0.2,
            "max_tokens": 1000,
        },
        timeout=40,
    )
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    return {**_extract_json(text), "available": True, "provider": provider}


def analyze_with_llm(headline: str) -> dict:
    """
    1) Search Google News
    2) LLM analyses claim + results (ChatGPT-style)
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
            "reason": "Text too short",
            "detailed_answer": "",
            "provider": None,
            "search_results": [],
        }

    search_results = search_web_for_claim(headline)
    search_block = _format_search_block(search_results)

    providers = [
        ("gemini", GEMINI_API_KEY, lambda h: _analyze_with_gemini(h, search_block)),
        ("groq", GROQ_API_KEY, lambda h: _openai_style(GROQ_URL, GROQ_API_KEY, GROQ_MODEL, h, search_block, "groq")),
        ("mistral", MISTRAL_API_KEY, lambda h: _openai_style(MISTRAL_URL, MISTRAL_API_KEY, MISTRAL_MODEL, h, search_block, "mistral")),
        ("openrouter", OPENROUTER_API_KEY, lambda h: _openai_style(
            OPENROUTER_URL, OPENROUTER_API_KEY, OPENROUTER_MODEL, h, search_block, "openrouter",
            {"HTTP-Referer": "https://github.com/anujwasnik0505-crypto/Fake-News-Detection", "X-Title": "Fake News Detection"},
        )),
    ]

    configured = False
    errors = []
    for name, key, fn in providers:
        if not key:
            continue
        configured = True
        try:
            result = fn(headline)
            if result.get("verdict") in {"PLAUSIBLE", "IMPLAUSIBLE"}:
                result["search_results"] = search_results
                result["search_count"] = len(search_results)
                return result
        except Exception as e:
            errors.append(f"{name}: {str(e)[:100]}")

    if not configured:
        return {
            "available": False,
            "verdict": None,
            "confidence": 0,
            "summary": "",
            "main_claim": "",
            "key_points": [],
            "reason": "No LLM API key. Set GEMINI_API_KEY.",
            "detailed_answer": "",
            "provider": None,
            "search_results": search_results,
        }

    return {
        "available": False,
        "verdict": None,
        "confidence": 0,
        "summary": "",
        "main_claim": "",
        "key_points": [],
        "reason": "LLM failed. " + " | ".join(errors),
        "detailed_answer": "",
        "provider": None,
        "search_results": search_results,
    }
