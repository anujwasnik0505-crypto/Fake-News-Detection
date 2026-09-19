"""
Phase-3: Image / screenshot / meme → text via OCR.

Supports:
- pytesseract (classic, needs system tesseract)
- easyocr (pure Python, heavier but no system deps)

Returns extracted text that can then be fed into the normal
headline / claim verification pipeline.
"""

from __future__ import annotations

import io
import os
import tempfile
from typing import BinaryIO

# Optional backends
try:
    import pytesseract
    from PIL import Image
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

try:
    import easyocr
    HAS_EASYOCR = True
    _easyocr_reader = None
except ImportError:
    HAS_EASYOCR = False
    _easyocr_reader = None


def _get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None and HAS_EASYOCR:
        # English + Hindi
        _easyocr_reader = easyocr.Reader(["en", "hi"], gpu=False, verbose=False)
    return _easyocr_reader


def _ocr_tesseract(image_bytes: bytes) -> str:
    img = Image.open(io.BytesIO(image_bytes))
    # Improve OCR on screenshots / memes
    text = pytesseract.image_to_string(img, lang="eng+hin")
    return (text or "").strip()


def _ocr_easyocr(image_bytes: bytes) -> str:
    reader = _get_easyocr_reader()
    if reader is None:
        raise RuntimeError("easyocr not available")
    # easyocr wants a file path or numpy array
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name
    try:
        results = reader.readtext(tmp_path, detail=0, paragraph=True)
        return "\n".join(results).strip()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def extract_text_from_image(image_bytes: bytes, prefer: str = "auto") -> dict:
    """
    Run OCR on image bytes.

    prefer: "tesseract" | "easyocr" | "auto"

    Returns:
    {
        "ok": bool,
        "text": str,
        "method": str,
        "error": str,
        "char_count": int,
    }
    """
    if not image_bytes:
        return {"ok": False, "text": "", "method": None,
                "error": "Empty image", "char_count": 0}

    order = []
    if prefer == "tesseract":
        order = ["tesseract", "easyocr"]
    elif prefer == "easyocr":
        order = ["easyocr", "tesseract"]
    else:
        # Prefer tesseract if available (lighter), else easyocr
        order = ["tesseract", "easyocr"]

    last_error = None
    for method in order:
        try:
            if method == "tesseract" and HAS_TESSERACT:
                text = _ocr_tesseract(image_bytes)
                if text:
                    return {
                        "ok": True,
                        "text": text,
                        "method": "tesseract",
                        "error": None,
                        "char_count": len(text),
                    }
            elif method == "easyocr" and HAS_EASYOCR:
                text = _ocr_easyocr(image_bytes)
                if text:
                    return {
                        "ok": True,
                        "text": text,
                        "method": "easyocr",
                        "error": None,
                        "char_count": len(text),
                    }
        except Exception as e:
            last_error = str(e)

    return {
        "ok": False,
        "text": "",
        "method": None,
        "error": last_error or (
            "No OCR backend available. Install pytesseract+tesseract "
            "or easyocr."
        ),
        "char_count": 0,
    }


def available_backends() -> list:
    backends = []
    if HAS_TESSERACT:
        backends.append("tesseract")
    if HAS_EASYOCR:
        backends.append("easyocr")
    return backends
