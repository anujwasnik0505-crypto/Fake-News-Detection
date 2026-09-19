"""
Phase-2: News URL → full article extraction.

Fetches a news article URL and extracts clean title + body text.
Uses multiple strategies so it works even without paid APIs:
1. trafilatura (best readability)
2. newspaper3k fallback
3. BeautifulSoup + simple heuristics as last resort
"""

import re
from urllib.parse import urlparse

import requests

# Optional heavy extractors — degrade gracefully if not installed
try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False

try:
    from newspaper import Article
    HAS_NEWSPAPER = True
except ImportError:
    HAS_NEWSPAPER = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


def _is_valid_url(url: str) -> bool:
    try:
        p = urlparse(url)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


def _clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _fetch_html(url: str, timeout: int = 12) -> str:
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
            allow_redirects=True,
        )
        resp.raise_for_status()
        # Prefer apparent encoding
        resp.encoding = resp.apparent_encoding or resp.encoding
        return resp.text
    except Exception:
        return None


def _extract_trafilatura(url: str, html: str) -> dict:
    if not HAS_TRAFILATURA:
        return None
    try:
        downloaded = html or trafilatura.fetch_url(url)
        if not downloaded:
            return None
        text = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
            favor_precision=True,
        )
        meta = trafilatura.extract_metadata(downloaded)
        title = (meta.title if meta else None) or ""
        if text and len(text) > 80:
            return {
                "title": _clean_text(title),
                "text": _clean_text(text),
                "method": "trafilatura",
            }
    except Exception:
        pass
    return None


def _extract_newspaper(url: str) -> dict:
    if not HAS_NEWSPAPER:
        return None
    try:
        art = Article(url, language="en")
        art.download()
        art.parse()
        text = _clean_text(art.text or "")
        title = _clean_text(art.title or "")
        if text and len(text) > 80:
            return {
                "title": title,
                "text": text,
                "method": "newspaper3k",
                "authors": art.authors or [],
                "publish_date": str(art.publish_date) if art.publish_date else None,
            }
    except Exception:
        pass
    return None


def _extract_bs4(html: str) -> dict:
    if not HAS_BS4 or not html:
        return None
    try:
        soup = BeautifulSoup(html, "html.parser")
        # Remove scripts/styles
        for tag in soup(["script", "style", "nav", "footer", "aside", "form"]):
            tag.decompose()

        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(" ", strip=True) or title

        # Prefer <article> or common content containers
        candidates = []
        for sel in ["article", "[role=main]", ".article-body", ".story-body",
                    ".post-content", ".entry-content", "main"]:
            node = soup.select_one(sel)
            if node:
                candidates.append(node.get_text(" ", strip=True))

        if not candidates:
            # Fallback: largest paragraph block
            paras = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
            text = " ".join(p for p in paras if len(p) > 40)
        else:
            text = max(candidates, key=len)

        text = _clean_text(text)
        title = _clean_text(title)
        if text and len(text) > 80:
            return {
                "title": title,
                "text": text,
                "method": "beautifulsoup",
            }
    except Exception:
        pass
    return None


def fetch_article(url: str) -> dict:
    """
    Fetch and extract article content from a URL.

    Returns:
    {
        "ok": bool,
        "url": str,
        "title": str,
        "text": str,
        "method": str,
        "error": str,
        "word_count": int,
    }
    """
    url = (url or "").strip()
    if not url:
        return {"ok": False, "url": url, "title": "", "text": "", "method": None,
                "error": "Empty URL", "word_count": 0}

    if not _is_valid_url(url):
        return {"ok": False, "url": url, "title": "", "text": "", "method": None,
                "error": "Invalid URL", "word_count": 0}

    html = _fetch_html(url)

    # Try extractors in order of quality
    result = _extract_trafilatura(url, html)
    if not result:
        result = _extract_newspaper(url)
    if not result:
        result = _extract_bs4(html or "")

    if not result:
        return {
            "ok": False,
            "url": url,
            "title": "",
            "text": "",
            "method": None,
            "error": "Could not extract article text (paywall / blocked / empty)",
            "word_count": 0,
        }

    text = result["text"]
    title = result.get("title") or ""
    words = len(text.split())

    return {
        "ok": True,
        "url": url,
        "title": title,
        "text": text,
        "method": result.get("method"),
        "error": None,
        "word_count": words,
        "authors": result.get("authors"),
        "publish_date": result.get("publish_date"),
    }


def is_url(text: str) -> bool:
    """Quick check if user input looks like a URL rather than a headline."""
    t = (text or "").strip()
    return t.startswith("http://") or t.startswith("https://") or (
        "." in t and " " not in t and len(t) < 300
    )
