"""
Phase-3: Claim extraction from full article text / OCR output.

Uses the same LLM providers already configured in llm_analysis.py
to pull out 2-6 short factual claims that can be verified independently.

Improvements:
- Strips bylines, publish dates, author lines, and other metadata
  before extraction (critical for OCR / screenshot text).
- Stronger filtering so metadata is never returned as a "claim".
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

# ---------------------------------------------------------------------------
# Metadata / byline patterns to strip (OCR + article text)
# ---------------------------------------------------------------------------

# Lines that are almost certainly not claims
_METADATA_LINE_PATTERNS = [
    # "By Author Name" / "By Author and Co-author"
    re.compile(
        r"^\s*(?:by|written\s+by|authored\s+by|reporter)\s*[:\-]?\s*[A-Z][A-Za-z.\s,&\-']{2,80}\s*$",
        re.IGNORECASE,
    ),
    # "Published September 21, 2026" / "Published: 21 Sep 2026"
    re.compile(
        r"^\s*(?:published|updated|posted|date)\s*[:\-]?\s*"
        r"(?:january|february|march|april|may|june|july|august|september|october|november|december|"
        r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)"
        r"[\s.,\d\-–—]*\d{2,4}\s*$",
        re.IGNORECASE,
    ),
    # Standalone date lines: "September 21, 2026" / "21 September 2026" / "2026-09-21"
    re.compile(
        r"^\s*(?:(?:january|february|march|april|may|june|july|august|september|october|november|december|"
        r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\s+\d{1,2},?\s+\d{4}"
        r"|\d{1,2}\s+(?:january|february|march|april|may|june|july|august|september|october|november|december|"
        r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\s+\d{4}"
        r"|\d{4}[-/]\d{1,2}[-/]\d{1,2})\s*$",
        re.IGNORECASE,
    ),
    # Source-only lines
    re.compile(
        r"^\s*(?:the\s+hindu|pti|ani|reuters|afp|ap\s+news|bbc|ndtv|times\s+of\s+india|"
        r"indian\s+express|hindustan\s+times|livemint|economic\s+times)\s*$",
        re.IGNORECASE,
    ),
    # Pure "Author Name and Author Name" without "By"
    re.compile(
        r"^\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}\s+(?:and|&)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}\s*$"
    ),
]

# Inline fragments to remove from a line
_INLINE_METADATA = [
    re.compile(
        r"\b(?:by|written\s+by)\s+[A-Z][A-Za-z.\s,&\-']{2,60}?"
        r"(?:\s+(?:and|&)\s+[A-Z][A-Za-z.\s,&\-']{2,40})?"
        r"(?:\s+(?:published|updated|posted)\s+[A-Za-z]+\s+\d{1,2},?\s+\d{4})?",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:published|updated|posted)\s*[:\-]?\s*"
        r"(?:january|february|march|april|may|june|july|august|september|october|november|december|"
        r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\s+\d{1,2},?\s+\d{4}",
        re.IGNORECASE,
    ),
]


def _is_metadata_line(line: str) -> bool:
    """Return True if the whole line looks like byline / date / source only."""
    s = line.strip()
    if not s or len(s) < 4:
        return True
    for pat in _METADATA_LINE_PATTERNS:
        if pat.match(s):
            return True
    # Very short lines that are mostly names
    if len(s) < 35 and re.match(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,4}$", s):
        return True
    return False


def _strip_inline_metadata(text: str) -> str:
    """Remove byline/date fragments that appear mid-sentence or at end of line."""
    for pat in _INLINE_METADATA:
        text = pat.sub(" ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_ocr_or_article_text(text: str) -> str:
    """
    Clean OCR / article text before claim extraction.

    - Removes pure byline, date, and source-only lines
    - Strips inline "By Author … Published Date" fragments
    - Removes OCR engine tags like [tesseract]
    - Keeps the actual headline and body
    """
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Strip OCR engine prefix tags
    text = re.sub(r"^\[(?:tesseract|gemini-vision|easyocr|gemini)\]\s*", "", text, flags=re.I)
    lines = text.split("\n")
    kept = []
    for ln in lines:
        if _is_metadata_line(ln):
            continue
        cleaned = _strip_inline_metadata(ln)
        if cleaned and not _is_metadata_line(cleaned):
            kept.append(cleaned)

    result = "\n".join(kept).strip()
    result = _strip_inline_metadata(result)
    return result


CLAIM_PROMPT = """You are a fact-checking assistant.
Extract the main factual claims from the news text below.

Rules:
- Return 2 to 6 short, self-contained factual claims.
- Each claim should be one sentence that can be verified as true or false.
- Ignore opinions, speculation, and rhetorical language.
- Prefer concrete claims (who did what, when, where, numbers).
- NEVER return bylines, author names, publish dates, source names, or metadata as claims.
  (Examples of things to IGNORE: "By Areena Arora and Gandla Sneha", "Published September 21, 2026", "The Hindu")
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


def _looks_like_metadata_claim(claim: str) -> bool:
    """Filter out any claim that is still just byline/date/source."""
    c = (claim or "").strip()
    if len(c) < 20:
        return True
    if _is_metadata_line(c):
        return True
    if re.search(r"\bby\s+[A-Z][a-z]+.*\bpublished\b", c, re.I):
        return True
    if re.match(r"^(?:by|published|updated|posted)\b", c, re.I) and len(c) < 90:
        return True
    return False


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
    return [
        c.strip()
        for c in claims
        if isinstance(c, str) and len(c.strip()) > 15 and not _looks_like_metadata_claim(c)
    ]


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
    return [
        c.strip()
        for c in claims
        if isinstance(c, str) and len(c.strip()) > 15 and not _looks_like_metadata_claim(c)
    ]


def _heuristic_claims(text: str, max_claims: int = 4) -> list:
    """Fallback when no LLM is available: split into sentences and keep longer ones."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    claims = []
    for s in sentences:
        s = s.strip()
        if _looks_like_metadata_claim(s):
            continue
        if 40 < len(s) < 220:
            if re.search(
                r"\b(said|announced|confirmed|reported|according|will|has|have|was|were|threat|tariff|deal)\b",
                s,
                re.I,
            ):
                claims.append(s)
            elif len(claims) < 2:
                claims.append(s)
        if len(claims) >= max_claims:
            break
    return claims


def extract_claims(text: str, max_claims: int = 5) -> dict:
    """
    Extract factual claims from article / long text / OCR output.

    Automatically cleans bylines, dates, and author metadata first.

    Returns:
    {
        "ok": bool,
        "claims": [str, ...],
        "method": "gemini" | "groq" | "heuristic" | None,
        "error": str,
        "cleaned_text_preview": str,
    }
    """
    raw = (text or "").strip()
    if not raw or len(raw) < 40:
        return {
            "ok": False,
            "claims": [],
            "method": None,
            "error": "Text too short for claim extraction",
        }

    # Clean metadata before anything else
    text = clean_ocr_or_article_text(raw)
    if not text or len(text) < 30:
        text = raw

    last_err = None

    if GEMINI_API_KEY:
        try:
            claims = _gemini_claims(text)[:max_claims]
            if claims:
                return {
                    "ok": True,
                    "claims": claims,
                    "method": "gemini",
                    "error": None,
                    "cleaned_text_preview": text[:400],
                }
        except Exception as e:
            last_err = str(e)

    if GROQ_API_KEY:
        try:
            claims = _groq_claims(text)[:max_claims]
            if claims:
                return {
                    "ok": True,
                    "claims": claims,
                    "method": "groq",
                    "error": None,
                    "cleaned_text_preview": text[:400],
                }
        except Exception as e:
            last_err = str(e)

    claims = _heuristic_claims(text, max_claims=max_claims)
    if claims:
        return {
            "ok": True,
            "claims": claims,
            "method": "heuristic",
            "error": last_err,
            "cleaned_text_preview": text[:400],
        }

    return {
        "ok": False,
        "claims": [],
        "method": None,
        "error": last_err or "Could not extract claims",
        "cleaned_text_preview": text[:400],
    }
