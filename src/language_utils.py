"""
Phase-2: Hindi + multilingual support.

- Detect language of headline / article
- Optionally translate non-English text to English for the ML model
  (ML models were trained mostly on English Kaggle data)
- Keep original text for display and for LLM layers (Gemini handles Hindi well)
"""

from __future__ import annotations

import re

try:
    from langdetect import detect, DetectorFactory
    DetectorFactory.seed = 0
    HAS_LANGDETECT = True
except ImportError:
    HAS_LANGDETECT = False

# Simple Devanagari range check (covers Hindi, Marathi, Sanskrit, etc.)
DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")


def detect_language(text: str) -> str:
    """
    Returns ISO 639-1 code (e.g. 'en', 'hi') or 'unknown'.
    Fast path for Devanagari script → 'hi'.
    """
    text = (text or "").strip()
    if not text:
        return "unknown"

    # Fast heuristic for Hindi / Hinglish with Devanagari
    if DEVANAGARI_RE.search(text):
        # If mostly Latin + some Devanagari → still treat as hi/hinglish
        return "hi"

    if not HAS_LANGDETECT:
        # Fallback: assume English if no Devanagari
        return "en"

    try:
        # langdetect struggles on very short strings
        sample = text if len(text) > 20 else text + " " + text
        code = detect(sample)
        return code or "unknown"
    except Exception:
        return "unknown"


def is_hindi_or_hinglish(text: str) -> bool:
    lang = detect_language(text)
    return lang in ("hi", "mr", "ne", "sa") or bool(DEVANAGARI_RE.search(text or ""))


def translate_to_english(text: str, source_lang: str = None) -> dict:
    """
    Best-effort translation to English for the ML model layer.

    Priority:
    1. Google Gemini (if GEMINI_API_KEY set) — free & good quality
    2. deep-translator (Google Translate free endpoint) if installed
    3. Return original text unchanged

    Returns:
    {
        "ok": bool,
        "translated": str,
        "source_lang": str,
        "method": str,
        "error": str,
    }
    """
    import os
    text = (text or "").strip()
    if not text:
        return {"ok": False, "translated": "", "source_lang": "unknown",
                "method": None, "error": "Empty text"}

    src = source_lang or detect_language(text)
    if src in ("en", "unknown"):
        return {"ok": True, "translated": text, "source_lang": src,
                "method": "passthrough", "error": None}

    # ---- Gemini ----
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if gemini_key:
        try:
            import requests
            url = (
                "https://generativelanguage.googleapis.com/"
                "v1beta/models/gemini-2.0-flash:generateContent"
            )
            prompt = (
                "Translate the following text to clear English. "
                "Return ONLY the translation, no explanation.\n\n"
                f"{text}"
            )
            resp = requests.post(
                url,
                params={"key": gemini_key},
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1024},
                },
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            translated = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            if translated:
                return {
                    "ok": True,
                    "translated": translated,
                    "source_lang": src,
                    "method": "gemini",
                    "error": None,
                }
        except Exception as e:
            pass  # fall through

    # ---- deep-translator ----
    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source="auto", target="en").translate(text)
        if translated:
            return {
                "ok": True,
                "translated": translated,
                "source_lang": src,
                "method": "deep_translator",
                "error": None,
            }
    except Exception:
        pass

    # Fallback: return original (LLM layers can still handle Hindi)
    return {
        "ok": False,
        "translated": text,
        "source_lang": src,
        "method": None,
        "error": "No translation backend available",
    }
