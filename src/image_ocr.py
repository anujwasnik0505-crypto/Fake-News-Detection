"""
Phase-3: Image / screenshot / meme → text via OCR.

Backends (in order):
1. Tesseract (if binary installed on server)
2. Gemini Vision API (if GEMINI_API_KEY set) — works on Render WITHOUT Docker
3. EasyOCR (if installed — heavy)

No system packages required when GEMINI_API_KEY is configured.
"""

from __future__ import annotations

import base64
import io
import os
import tempfile

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
HAS_TESSERACT = False
HAS_PIL = False
HAS_EASYOCR = False
_easyocr_reader = None

try:
    from PIL import Image, ImageOps
    HAS_PIL = True
except ImportError:
    pass

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    pass

try:
    import easyocr
    HAS_EASYOCR = True
except ImportError:
    pass

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()


def _get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None and HAS_EASYOCR:
        try:
            _easyocr_reader = easyocr.Reader(["en", "hi"], gpu=False, verbose=False)
        except Exception:
            _easyocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    return _easyocr_reader


def _prepare_image(image_bytes):
    if not HAS_PIL:
        raise RuntimeError("Pillow not installed. pip install Pillow")
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    w, h = img.size
    if max(w, h) < 800:
        scale = max(2, int(800 / max(w, h)))
        img = img.resize((w * scale, h * scale), Image.Resampling.LANCZOS)
    try:
        img = ImageOps.autocontrast(img)
    except Exception:
        pass
    return img


def _ocr_tesseract(image_bytes):
    if not HAS_TESSERACT:
        raise RuntimeError("pytesseract not installed")
    img = _prepare_image(image_bytes)
    last_err = None
    for lang in ("eng+hin", "eng"):
        try:
            text = pytesseract.image_to_string(img, lang=lang)
            text = (text or "").strip()
            if text:
                return text
        except Exception as e:
            last_err = e
            continue
    if last_err:
        raise last_err
    return ""


def _ocr_gemini_vision(image_bytes):
    """Extract text using Gemini multimodal — no system tesseract needed."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")

    # Compress large images to stay under API limits
    mime = "image/jpeg"
    b64 = None
    if HAS_PIL:
        try:
            img = Image.open(io.BytesIO(image_bytes))
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            # max side 1600
            w, h = img.size
            max_side = 1600
            if max(w, h) > max_side:
                scale = max_side / float(max(w, h))
                img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            mime = "image/jpeg"
        except Exception:
            b64 = None

    if not b64:
        b64 = base64.b64encode(image_bytes).decode("ascii")
        # guess mime
        if image_bytes[:8].startswith(b"\x89PNG"):
            mime = "image/png"
        elif image_bytes[:2] == b"\xff\xd8":
            mime = "image/jpeg"
        else:
            mime = "image/jpeg"

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/gemini-2.0-flash:generateContent"
    )
    prompt = (
        "Extract ALL readable text from this image exactly as written. "
        "Include headlines, captions, and body text. "
        "Preserve line breaks where helpful. "
        "Do not translate. Do not add commentary. "
        "If the image has no text, reply with exactly: NO_TEXT"
    )
    resp = requests.post(
        url,
        params={"key": GEMINI_API_KEY},
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime, "data": b64}},
                ]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 2048,
            },
        },
        timeout=40,
    )
    resp.raise_for_status()
    data = resp.json()
    text = (
        data.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "")
        or ""
    ).strip()
    if not text or text.upper() == "NO_TEXT":
        return ""
    return text


def _ocr_easyocr(image_bytes):
    reader = _get_easyocr_reader()
    if reader is None:
        raise RuntimeError("easyocr not available")
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name
    try:
        results = reader.readtext(tmp_path, detail=0, paragraph=True)
        if isinstance(results, list):
            return "\n".join(str(r) for r in results).strip()
        return str(results or "").strip()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def extract_text_from_image(image_bytes, prefer="auto"):
    """
    Run OCR on image bytes.

    prefer: "tesseract" | "gemini" | "easyocr" | "auto"
    """
    if not image_bytes:
        return {
            "ok": False, "text": "", "method": None,
            "error": "Empty image data", "char_count": 0,
        }

    if prefer == "tesseract":
        order = ["tesseract", "gemini", "easyocr"]
    elif prefer == "gemini":
        order = ["gemini", "tesseract", "easyocr"]
    elif prefer == "easyocr":
        order = ["easyocr", "gemini", "tesseract"]
    else:
        # Prefer Gemini on cloud hosts (no system binary needed), then tesseract
        order = ["gemini", "tesseract", "easyocr"]

    last_error = None
    tried = []

    for method in order:
        try:
            if method == "gemini":
                if not GEMINI_API_KEY:
                    continue
                tried.append("gemini")
                text = _ocr_gemini_vision(image_bytes)
                if text and len(text.strip()) >= 3:
                    return {
                        "ok": True,
                        "text": text.strip(),
                        "method": "gemini-vision",
                        "error": None,
                        "char_count": len(text.strip()),
                    }
                last_error = "Gemini Vision found no readable text in the image"

            elif method == "tesseract":
                if not HAS_TESSERACT or not HAS_PIL:
                    continue
                tried.append("tesseract")
                text = _ocr_tesseract(image_bytes)
                if text and len(text.strip()) >= 3:
                    return {
                        "ok": True,
                        "text": text.strip(),
                        "method": "tesseract",
                        "error": None,
                        "char_count": len(text.strip()),
                    }
                last_error = "Tesseract returned empty text"

            elif method == "easyocr":
                if not HAS_EASYOCR:
                    continue
                tried.append("easyocr")
                text = _ocr_easyocr(image_bytes)
                if text and len(text.strip()) >= 3:
                    return {
                        "ok": True,
                        "text": text.strip(),
                        "method": "easyocr",
                        "error": None,
                        "char_count": len(text.strip()),
                    }
                last_error = "EasyOCR returned empty text"

        except Exception as e:
            msg = str(e)
            if "TesseractNotFound" in msg or "tesseract is not installed" in msg.lower():
                last_error = "Tesseract binary not on server (skipped)"
            else:
                last_error = msg[:200]
            continue

    if not tried:
        return {
            "ok": False,
            "text": "",
            "method": None,
            "error": (
                "No OCR backend available. "
                "Set GEMINI_API_KEY in Render Environment (easiest), "
                "or install Tesseract via Docker."
            ),
            "char_count": 0,
            "backends": available_backends(),
        }

    return {
        "ok": False,
        "text": "",
        "method": None,
        "error": last_error or "OCR failed",
        "char_count": 0,
        "backends": available_backends(),
        "tried": tried,
    }


def available_backends():
    backends = []
    if GEMINI_API_KEY:
        backends.append("gemini-vision")
    if HAS_TESSERACT and HAS_PIL:
        backends.append("tesseract")
    if HAS_EASYOCR:
        backends.append("easyocr")
    return backends
