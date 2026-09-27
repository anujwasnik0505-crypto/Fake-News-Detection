"""
Normalize any user input so the 5-layer pipeline always gets usable text.

Handles:
- 2–3 word phrases  → still verified (ML + LLM + red-flag)
- Full paragraphs   → extract main claim / first strong sentence
- Very long articles → truncate smartly for search layers
"""

from __future__ import annotations

import re


def clean_raw_input(text: str) -> str:
    """Basic cleanup: whitespace, OCR tags, control chars."""
    if not text:
        return ""
    t = str(text).replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"^\[(?:tesseract|gemini-vision|easyocr|gemini)\]\s*", "", t, flags=re.I)
    t = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def extract_primary_claim(text: str, max_chars: int = 280) -> str:
    """
    From a paragraph / long text, pick the best short claim for
    verification layers (search, fact-check, red-flag, ML).

    Priority:
    1. First non-metadata sentence that looks like news
    2. First line longer than ~20 chars
    3. Truncated full text
    """
    text = clean_raw_input(text)
    if not text:
        return ""

    # Already short → use as-is
    if len(text) <= max_chars and text.count("\n") <= 1:
        return text

    # Split into sentences
    sentences = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
    sentences = [s.strip() for s in sentences if s.strip()]

    # Prefer sentences that look like news claims
    news_hint = re.compile(
        r"\b(said|announced|confirmed|reported|will|has|have|was|were|"
        r"government|minister|president|court|police|ban|tariff|deal|"
        r"killed|died|wins|launches|passes|approves)\b",
        re.I,
    )

    for s in sentences:
        if len(s) < 15:
            continue
        # Skip pure bylines / dates
        if re.match(r"^(by|published|updated|posted)\b", s, re.I):
            continue
        if news_hint.search(s) or len(s) > 40:
            return s[:max_chars]

    # Fallback: first substantial line
    for line in text.split("\n"):
        line = line.strip()
        if len(line) >= 20:
            return line[:max_chars]

    return text[:max_chars]


def prepare_input(raw: str) -> dict:
    """
    Prepare any user input for the verification pipeline.

    Returns:
    {
        "ok": bool,
        "raw": str,
        "headline": str,      # short form for search / ML / red-flag
        "full_text": str,     # full text for LLM analysis
        "input_kind": "phrase" | "headline" | "paragraph",
        "word_count": int,
        "error": str | None,
    }
    """
    raw = clean_raw_input(raw)
    if not raw:
        return {
            "ok": False,
            "raw": "",
            "headline": "",
            "full_text": "",
            "input_kind": "empty",
            "word_count": 0,
            "error": "Empty input",
        }

    words = re.findall(r"[A-Za-z0-9\u0900-\u097F]+", raw)
    word_count = len(words)

    # Allow as little as 2 words (user request)
    if word_count < 2 and len(raw) < 6:
        return {
            "ok": False,
            "raw": raw,
            "headline": raw,
            "full_text": raw,
            "input_kind": "too_short",
            "word_count": word_count,
            "error": "Please enter at least 2 words or a short phrase",
        }

    if word_count <= 12 and len(raw) <= 120:
        kind = "phrase" if word_count <= 5 else "headline"
        headline = raw
        full_text = raw
    else:
        kind = "paragraph"
        headline = extract_primary_claim(raw, max_chars=300)
        full_text = raw[:4000]  # cap for LLM cost/latency

    return {
        "ok": True,
        "raw": raw,
        "headline": headline,
        "full_text": full_text,
        "input_kind": kind,
        "word_count": word_count,
        "error": None,
    }
