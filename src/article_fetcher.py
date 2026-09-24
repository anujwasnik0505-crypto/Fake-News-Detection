"""
Phase-2: News URL → full article extraction.

Strategies (in order):
1. trafilatura (if installed)
2. newspaper3k (if installed)
3. BeautifulSoup / html.parser heuristics
4. Regex paragraph fallback (always available)
"""

from __future__ import annotations

import re
from urllib.parse import urlparse, urljoin

import requests

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

MIN_TEXT_LEN = 40  # was 80 — too strict for short articles


def _normalize_url(url):
    url = (url or "").strip()
    if not url:
        return ""
    if url.startswith("//"):
        url = "https:" + url
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    return url


def _is_valid_url(url):
    try:
        p = urlparse(url)
        return p.scheme in ("http", "https") and bool(p.netloc) and "." in p.netloc
    except Exception:
        return False


def _clean_text(text):
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _fetch_html(url, timeout=15):
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
        "Cache-Control": "no-cache",
    }
    try:
        resp = requests.get(
            url,
            headers=headers,
            timeout=timeout,
            allow_redirects=True,
        )
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or resp.encoding or "utf-8"
        return resp.text, None
    except requests.exceptions.Timeout:
        return None, "Request timed out while fetching the URL"
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response is not None else "?"
        return None, "HTTP %s — site blocked the request or page not found" % code
    except requests.exceptions.RequestException as e:
        return None, "Network error: %s" % (str(e)[:120])
    except Exception as e:
        return None, "Fetch failed: %s" % (str(e)[:120])


def _extract_trafilatura(url, html):
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
        if text and len(text) > MIN_TEXT_LEN:
            return {
                "title": _clean_text(title),
                "text": _clean_text(text),
                "method": "trafilatura",
            }
    except Exception:
        pass
    return None


def _extract_newspaper(url):
    if not HAS_NEWSPAPER:
        return None
    try:
        art = Article(url)
        art.download()
        art.parse()
        text = _clean_text(art.text or "")
        title = _clean_text(art.title or "")
        if text and len(text) > MIN_TEXT_LEN:
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


def _extract_bs4(html):
    if not HAS_BS4 or not html:
        return None
    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "aside", "form", "noscript"]):
            tag.decompose()

        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(" ", strip=True) or title

        candidates = []
        for sel in [
            "article", "[role=main]", ".article-body", ".story-body",
            ".post-content", ".entry-content", "main", ".content",
            "#content", ".article__body", ".story__content",
        ]:
            node = soup.select_one(sel)
            if node:
                candidates.append(node.get_text(" ", strip=True))

        if not candidates:
            paras = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
            text = " ".join(p for p in paras if len(p) > 30)
        else:
            text = max(candidates, key=len)

        text = _clean_text(text)
        title = _clean_text(title)
        if text and len(text) > MIN_TEXT_LEN:
            return {"title": title, "text": text, "method": "beautifulsoup"}
    except Exception:
        pass
    return None


def _extract_regex(html):
    """Last-resort extractor — no extra deps."""
    if not html:
        return None
    try:
        title = ""
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        if m:
            title = re.sub(r"<[^>]+>", "", m.group(1))
        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.I | re.S)
        if h1:
            title = re.sub(r"<[^>]+>", "", h1.group(1)) or title

        # strip scripts/styles
        cleaned = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.I | re.S)
        cleaned = re.sub(r"<style[^>]*>.*?</style>", " ", cleaned, flags=re.I | re.S)
        paras = re.findall(r"<p[^>]*>(.*?)</p>", cleaned, re.I | re.S)
        texts = []
        for p in paras:
            t = re.sub(r"<[^>]+>", " ", p)
            t = _clean_text(t)
            if len(t) > 30:
                texts.append(t)
        text = _clean_text(" ".join(texts))
        title = _clean_text(title)
        if text and len(text) > MIN_TEXT_LEN:
            return {"title": title, "text": text, "method": "regex"}
    except Exception:
        pass
    return None


def fetch_article(url):
    """
    Fetch and extract article content from a URL.

    Returns:
      ok, url, title, text, method, error, word_count
    """
    url = _normalize_url(url)
    if not url:
        return {
            "ok": False, "url": url, "title": "", "text": "",
            "method": None, "error": "Empty URL", "word_count": 0,
        }

    if not _is_valid_url(url):
        return {
            "ok": False, "url": url, "title": "", "text": "",
            "method": None, "error": "Invalid URL. Use full link like https://www.thehindu.com/...",
            "word_count": 0,
        }

    html, fetch_err = _fetch_html(url)

    result = None
    if html:
        result = _extract_trafilatura(url, html)
    if not result:
        result = _extract_newspaper(url)
    if not result and html:
        result = _extract_bs4(html)
    if not result and html:
        result = _extract_regex(html)

    if not result:
        # Even if body empty, use page title as headline if we got HTML
        if html:
            title_only = ""
            m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
            if m:
                title_only = _clean_text(re.sub(r"<[^>]+>", "", m.group(1)))
            if title_only and len(title_only) > 15:
                return {
                    "ok": True,
                    "url": url,
                    "title": title_only,
                    "text": title_only,
                    "method": "title_only",
                    "error": None,
                    "word_count": len(title_only.split()),
                }

        err = fetch_err or "Could not extract article text (paywall / blocked / JS-only page)"
        installed = []
        if HAS_TRAFILATURA:
            installed.append("trafilatura")
        if HAS_NEWSPAPER:
            installed.append("newspaper3k")
        if HAS_BS4:
            installed.append("bs4")
        hint = ""
        if not installed:
            hint = " Install: pip install trafilatura beautifulsoup4 lxml"
        return {
            "ok": False,
            "url": url,
            "title": "",
            "text": "",
            "method": None,
            "error": err + hint,
            "word_count": 0,
        }

    text = result["text"]
    title = result.get("title") or ""
    return {
        "ok": True,
        "url": url,
        "title": title,
        "text": text,
        "method": result.get("method"),
        "error": None,
        "word_count": len(text.split()),
        "authors": result.get("authors"),
        "publish_date": result.get("publish_date"),
    }


def is_url(text):
    """True if input looks like a URL rather than a headline."""
    t = (text or "").strip()
    if not t:
        return False
    if t.startswith("http://") or t.startswith("https://") or t.startswith("//"):
        return True
    # domain-like without spaces
    if " " in t or len(t) > 400:
        return False
    if re.match(r"^[a-zA-Z0-9][-a-zA-Z0-9.]*\.[a-zA-Z]{2,}(/.*)?$", t):
        return True
    return False
