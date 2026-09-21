"""
Phase-3: Image / screenshot / meme → text via OCR.

Supports:
- pytesseract + system Tesseract OCR
- easyocr as fallback

Works on:
- Windows (local development)
- Linux / Render deployment

Returns extracted text that can then be fed into the normal
headline / claim verification pipeline.
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import tempfile
from typing import Optional

# ============================================================
# OPTIONAL IMPORTS
# ============================================================

try:
    import pytesseract
    from PIL import Image

    HAS_PYTESSERACT = True
except ImportError:
    pytesseract = None
    Image = None
    HAS_PYTESSERACT = False


try:
    import easyocr

    HAS_EASYOCR = True
    _easyocr_reader = None
except ImportError:
    easyocr = None
    HAS_EASYOCR = False
    _easyocr_reader = None


# ============================================================
# TESSERACT CONFIGURATION
# ============================================================

def _find_tesseract() -> Optional[str]:
    """
    Find the Tesseract executable.

    Priority:
    1. TESSERACT_CMD environment variable
    2. PATH
    3. Common Windows installation paths
    4. Common Linux paths
    """

    # --------------------------------------------------------
    # 1. Environment variable
    # --------------------------------------------------------
    env_path = os.environ.get("TESSERACT_CMD")

    if env_path:
        env_path = os.path.expandvars(env_path.strip().strip('"'))

        if os.path.isfile(env_path):
            return env_path

        found_env = shutil.which(env_path)
        if found_env:
            return found_env

    # --------------------------------------------------------
    # 2. Search PATH
    # --------------------------------------------------------
    path_result = shutil.which("tesseract")

    if path_result:
        return path_result

    # --------------------------------------------------------
    # 3. Common Windows locations
    # --------------------------------------------------------
    windows_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(
            r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"
        ),
    ]

    for path in windows_paths:
        if os.path.isfile(path):
            return path

    # --------------------------------------------------------
    # 4. Common Linux locations
    # --------------------------------------------------------
    linux_paths = [
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
        "/opt/homebrew/bin/tesseract",
    ]

    for path in linux_paths:
        if os.path.isfile(path):
            return path

    return None


def _configure_tesseract() -> Optional[str]:
    """
    Configure pytesseract with the detected Tesseract executable.
    Returns the executable path if available.
    """

    if not HAS_PYTESSERACT:
        return None

    tesseract_path = _find_tesseract()

    if not tesseract_path:
        return None

    try:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
    except Exception:
        return None

    return tesseract_path


TESSERACT_PATH = _configure_tesseract()


# ============================================================
# TESSERACT VALIDATION
# ============================================================

def _is_tesseract_available() -> bool:
    """
    Check whether the Tesseract executable actually works.
    """

    if not HAS_PYTESSERACT:
        return False

    global TESSERACT_PATH

    if not TESSERACT_PATH:
        TESSERACT_PATH = _configure_tesseract()

    if not TESSERACT_PATH:
        return False

    try:
        subprocess.run(
            [TESSERACT_PATH, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=False,
        )

        return True

    except Exception:
        return False


HAS_TESSERACT = _is_tesseract_available()


# ============================================================
# TESSERACT LANGUAGE DETECTION
# ============================================================

def _get_tesseract_languages() -> list[str]:
    """
    Return installed Tesseract languages.
    """

    if not HAS_TESSERACT:
        return []

    try:
        languages = pytesseract.get_languages(config="")
        return languages or []
    except Exception:
        return []


def _select_tesseract_language() -> str:
    """
    Select the best available OCR language.

    Preferred:
        eng+hin

    Fallback:
        eng

    Final fallback:
        first available language
    """

    languages = _get_tesseract_languages()

    if "eng" in languages and "hin" in languages:
        return "eng+hin"

    if "eng" in languages:
        return "eng"

    if "hin" in languages:
        return "hin"

    if languages:
        return languages[0]

    # If language detection fails, use English.
    return "eng"


# ============================================================
# EASYOCR
# ============================================================

def _get_easyocr_reader():
    """
    Create EasyOCR reader only when needed.
    """

    global _easyocr_reader

    if _easyocr_reader is None and HAS_EASYOCR:
        try:
            _easyocr_reader = easyocr.Reader(
                ["en", "hi"],
                gpu=False,
                verbose=False,
            )
        except Exception:
            _easyocr_reader = None

    return _easyocr_reader


# ============================================================
# TESSERACT OCR
# ============================================================

def _ocr_tesseract(image_bytes: bytes) -> str:
    """
    Extract text using Tesseract OCR.
    """

    if not HAS_PYTESSERACT:
        raise RuntimeError(
            "pytesseract is not installed."
        )

    if not HAS_TESSERACT:
        raise RuntimeError(
            "Tesseract OCR is not installed or is not available in PATH."
        )

    if Image is None:
        raise RuntimeError(
            "Pillow is not installed."
        )

    # --------------------------------------------------------
    # Make sure Tesseract is configured
    # --------------------------------------------------------
    global TESSERACT_PATH

    if not TESSERACT_PATH:
        TESSERACT_PATH = _configure_tesseract()

    if not TESSERACT_PATH:
        raise RuntimeError(
            "Tesseract executable could not be found."
        )

    # --------------------------------------------------------
    # Open image
    # --------------------------------------------------------
    try:
        img = Image.open(io.BytesIO(image_bytes))

        # Convert problematic image formats to RGB
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

    except Exception as e:
        raise RuntimeError(
            f"Unable to open image: {e}"
        )

    # --------------------------------------------------------
    # Select installed language
    # --------------------------------------------------------
    language = _select_tesseract_language()

    # --------------------------------------------------------
    # OCR
    # --------------------------------------------------------
    try:
        text = pytesseract.image_to_string(
            img,
            lang=language,
            config="--psm 6",
        )

    except Exception as e:
        # ----------------------------------------------------
        # If Hindi trained data is unavailable, retry English
        # ----------------------------------------------------
        if language == "eng+hin":
            try:
                text = pytesseract.image_to_string(
                    img,
                    lang="eng",
                    config="--psm 6",
                )
            except Exception as second_error:
                raise RuntimeError(
                    f"Tesseract OCR failed: {second_error}"
                )
        else:
            raise RuntimeError(
                f"Tesseract OCR failed: {e}"
            )

    return (text or "").strip()


# ============================================================
# EASYOCR OCR
# ============================================================

def _ocr_easyocr(image_bytes: bytes) -> str:
    """
    Extract text using EasyOCR.
    """

    reader = _get_easyocr_reader()

    if reader is None:
        raise RuntimeError(
            "EasyOCR is not available."
        )

    # EasyOCR can read from a temporary image file.
    with tempfile.NamedTemporaryFile(
        suffix=".png",
        delete=False,
    ) as tmp:

        tmp.write(image_bytes)
        tmp_path = tmp.name

    try:
        results = reader.readtext(
            tmp_path,
            detail=0,
            paragraph=True,
        )

        if not results:
            return ""

        return "\n".join(
            str(item).strip()
            for item in results
            if str(item).strip()
        ).strip()

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ============================================================
# MAIN OCR FUNCTION
# ============================================================

def extract_text_from_image(
    image_bytes: bytes,
    prefer: str = "auto",
) -> dict:
    """
    Run OCR on image bytes.

    prefer:
        "tesseract"
        "easyocr"
        "auto"

    Returns:
    {
        "ok": bool,
        "text": str,
        "method": str | None,
        "error": str | None,
        "char_count": int,
    }
    """

    # --------------------------------------------------------
    # Empty image check
    # --------------------------------------------------------
    if not image_bytes:
        return {
            "ok": False,
            "text": "",
            "method": None,
            "error": "Empty image.",
            "char_count": 0,
        }

    # --------------------------------------------------------
    # Normalize preference
    # --------------------------------------------------------
    prefer = (prefer or "auto").lower().strip()

    if prefer not in {
        "auto",
        "tesseract",
        "easyocr",
    }:
        prefer = "auto"

    # --------------------------------------------------------
    # Decide OCR order
    # --------------------------------------------------------
    if prefer == "tesseract":
        order = [
            "tesseract",
            "easyocr",
        ]

    elif prefer == "easyocr":
        order = [
            "easyocr",
            "tesseract",
        ]

    else:
        # Tesseract is lightweight, so use it first.
        order = [
            "tesseract",
            "easyocr",
        ]

    # --------------------------------------------------------
    # Try OCR backends
    # --------------------------------------------------------
    errors = []

    for method in order:

        # ====================================================
        # TESSERACT
        # ====================================================
        if method == "tesseract":

            if not HAS_PYTESSERACT:
                errors.append(
                    "pytesseract is not installed."
                )
                continue

            if not HAS_TESSERACT:
                errors.append(
                    "Tesseract OCR is not installed or is not in PATH."
                )
                continue

            try:
                text = _ocr_tesseract(image_bytes)

                if text:
                    return {
                        "ok": True,
                        "text": text,
                        "method": "tesseract",
                        "error": None,
                        "char_count": len(text),
                    }

                errors.append(
                    "Tesseract ran successfully but no text was detected."
                )

            except Exception as e:
                errors.append(
                    f"Tesseract: {str(e)}"
                )

        # ====================================================
        # EASYOCR
        # ====================================================
        elif method == "easyocr":

            if not HAS_EASYOCR:
                errors.append(
                    "EasyOCR is not installed."
                )
                continue

            try:
                text = _ocr_easyocr(image_bytes)

                if text:
                    return {
                        "ok": True,
                        "text": text,
                        "method": "easyocr",
                        "error": None,
                        "char_count": len(text),
                    }

                errors.append(
                    "EasyOCR ran successfully but no text was detected."
                )

            except Exception as e:
                errors.append(
                    f"EasyOCR: {str(e)}"
                )

    # ========================================================
    # ALL OCR METHODS FAILED
    # ========================================================

    if errors:
        error_message = " | ".join(errors)
    else:
        error_message = (
            "No OCR backend is available. "
            "Install pytesseract + Tesseract OCR or EasyOCR."
        )

    return {
        "ok": False,
        "text": "",
        "method": None,
        "error": error_message,
        "char_count": 0,
    }


# ============================================================
# BACKEND INFORMATION
# ============================================================

def available_backends() -> list:
    """
    Return currently available OCR backends.
    """

    backends = []

    if HAS_TESSERACT:
        backends.append("tesseract")

    if HAS_EASYOCR:
        backends.append("easyocr")

    return backends


# ============================================================
# OCR STATUS
# ============================================================

def ocr_status() -> dict:
    """
    Return useful diagnostic information.

    Helpful for debugging Render/local deployment.
    """

    languages = []

    if HAS_TESSERACT:
        languages = _get_tesseract_languages()

    return {
        "tesseract": {
            "python_package": HAS_PYTESSERACT,
            "executable": HAS_TESSERACT,
            "path": TESSERACT_PATH,
            "languages": languages,
        },
        "easyocr": {
            "available": HAS_EASYOCR,
        },
        "backends": available_backends(),
    }
