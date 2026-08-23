"""
Cross-verification: check if a headline is corroborated by trusted news outlets
right now. Uses NewsAPI.org (https://newsapi.org) as the primary check when an API
key is configured, and falls back to free Google News RSS search otherwise — so the
project works even without a key, but upgrades automatically once one is added.
"""
import os
import re
from urllib.parse import quote
import feedparser
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()  # reads NEWSAPI_KEY from a .env file in the project root, if present
except ImportError:
    pass  # python-dotenv not installed — NEWSAPI_KEY can still be set as a real env var

# Expanded list — includes major national wires/outlets AND commonly-cited Indian
# regional/digital outlets that a short "big name only" whitelist misses.
TRUSTED_SOURCE_NAMES = [
    "reuters", "bbc", "associated press", "ap news", "the hindu", "ndtv",
    "times of india", "indian express", "hindustan times", "al jazeera",
    "cnn", "the guardian", "npr", "pti", "ani", "livemint", "economic times",
    "deccan herald", "free press journal", "asianet newsable", "asianet news",
    "awaz the voice", "news18", "india today", "zee news", "republic",
    "moneycontrol", "the print", "scroll", "outlook india", "the wire",
    "business standard", "dna india", "mid-day", "loksatta", "lokmat",
    "sakal", "maharashtra times", "abp", "tv9", "aaj tak",
]

# Stopwords stripped before comparing headlines — keeps the overlap check
# focused on words that actually carry the story (names, places, event).
_STOPWORDS = {
    "a", "an", "the", "in", "on", "at", "of", "to", "and", "for", "is",
    "was", "after", "over", "with", "die", "dies", "died", "three", "3",
}


def _normalize_source(name):
    return re.sub(r"[^a-z0-9 ]", "", (name or "").lower()).strip()


def _tokenize(text):
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def _similarity(a, b):
    """Token-overlap (Jaccard) similarity — robust to headlines that describe
    the same event in completely different words/word-order, unlike a raw
    character-sequence match."""
    tokens_a, tokens_b = _tokenize(a), _tokenize(b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


SIMILARITY_THRESHOLD = 0.30  # tuned for token-overlap scoring, not char-ratio
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "")  # set this in .env or as an env var
NEWSAPI_URL = "https://newsapi.org/v2/everything"


def _search_newsapi(query, limit=20):
    """Search NewsAPI.org for the headline. Returns None if no key set or request fails."""
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
    News RSS search otherwise, on any error, OR if NewsAPI returns zero results
    (common with free-tier's 24h delay on very recent stories).

    Returns: {"verified": bool, "matched_sources": [...], "num_checked": int, "provider": str}
    """
    provider = "newsapi"
    try:
        results = _search_newsapi(headline)
        # Fallback to RSS not just on error/None, but also when NewsAPI's
        # free-tier delay or strict query matching returns an empty list.
        if not results:
            provider = "google_news_rss"
            results = _search_google_news(headline)
    except Exception:
        return {"verified": False, "matched_sources": [], "num_checked": 0, "error": True, "provider": provider}

    matched_sources = []
    for r in results:
        sim = _similarity(headline, r["title"])
        source_norm = _normalize_source(r["source"])
        is_trusted = any(name in source_norm for name in TRUSTED_SOURCE_NAMES)
        if sim >= SIMILARITY_THRESHOLD and is_trusted:
            matched_sources.append({"title": r["title"], "source": r["source"], "similarity": round(sim, 2)})

    return {
        "verified": len(matched_sources) > 0,
        "matched_sources": matched_sources,
        "num_checked": len(results),
        "error": False,
        "provider": provider,
    }