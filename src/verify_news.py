"""
Cross-verification: check if a headline is corroborated by trusted news outlets
right now. Uses NewsAPI.org (https://newsapi.org) as the primary check when an API
key is configured, and falls back to free Google News RSS search otherwise — so the
project works even without a key, but upgrades automatically once one is added.
"""
import os
from difflib import SequenceMatcher
from urllib.parse import quote
import feedparser
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()  # reads NEWSAPI_KEY from a .env file in the project root, if present
except ImportError:
    pass  # python-dotenv not installed — NEWSAPI_KEY can still be set as a real env var

TRUSTED_SOURCE_NAMES = [
    "reuters", "bbc", "associated press", "ap news", "the hindu", "ndtv",
    "times of india", "indian express", "hindustan times", "al jazeera",
    "cnn", "the guardian", "npr", "pti", "ani", "livemint", "economic times",
]

SIMILARITY_THRESHOLD = 0.45
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "")  # set this in .env or as an env var
NEWSAPI_URL = "https://newsapi.org/v2/everything"


def _similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _search_newsapi(query, limit=20):
    """Search NewsAPI.org for the headline. Returns [] if no key set or request fails."""
    if not NEWSAPI_KEY:
        return None  # signals "not configured" so caller can fall back to RSS
    try:
        resp = requests.get(
            NEWSAPI_URL,
            params={
                "q": query,
                "language": "en",
                "sortBy": "relevancy",
                "pageSize": limit,
                "apiKey": NEWSAPI_KEY,
            },
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for article in data.get("articles", []):
            source_name = (article.get("source") or {}).get("name", "")
            title = article.get("title", "")
            if title:
                results.append({"title": title, "source": source_name})
        return results
    except Exception:
        return None  # fall back to RSS on any error (rate limit, network, etc.)


def _search_google_news(query, limit=20):
    url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-IN&gl=IN&ceid=IN:en"
    feed = feedparser.parse(url)
    results = []
    for entry in feed.entries[:limit]:
        source_name = entry.source.title if hasattr(entry, "source") else ""
        results.append({"title": entry.title, "source": source_name})
    return results


def verify_headline(headline):
    """Search live news for corroboration from trusted outlets.

    Tries NewsAPI.org first (if NEWSAPI_KEY is set), falls back to free Google
    News RSS search otherwise or if the API call fails.

    Returns: {"verified": bool, "matched_sources": [...], "num_checked": int, "provider": str}
    """
    provider = "newsapi"
    try:
        results = _search_newsapi(headline)
        if results is None:  # no key configured, or the request failed
            provider = "google_news_rss"
            results = _search_google_news(headline)
    except Exception:
        return {"verified": False, "matched_sources": [], "num_checked": 0, "error": True, "provider": provider}

    matched_sources = []
    for r in results:
        sim = _similarity(headline, r["title"])
        source_lower = (r["source"] or "").lower()
        is_trusted = any(name in source_lower for name in TRUSTED_SOURCE_NAMES)
        if sim >= SIMILARITY_THRESHOLD and is_trusted:
            matched_sources.append({"title": r["title"], "source": r["source"], "similarity": round(sim, 2)})

    return {
        "verified": len(matched_sources) > 0,
        "matched_sources": matched_sources,
        "num_checked": len(results),
        "error": False,
        "provider": provider,
    }
