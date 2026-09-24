"""
Cross-verification: check if a headline is corroborated by trusted news outlets
right now. Uses NewsAPI.org as primary check when a key is set, falls back to
free Google News RSS otherwise.

Improvements:
- Better query building (key phrases, not full long headline)
- Lower but smarter similarity + partial phrase matching
- Stronger source-name normalization (handles "The Hindu", "thehindu.com", etc.)
- Extra Indian + international trusted outlets
"""

import os
import re
from urllib.parse import quote

import feedparser
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Expanded trusted sources (lowercase matching)
TRUSTED_SOURCE_NAMES = [
    "reuters", "bbc", "associated press", "ap news", "the hindu", "hindu",
    "ndtv", "times of india", "indian express", "hindustan times",
    "al jazeera", "cnn", "the guardian", "npr", "pti", "ani",
    "livemint", "economic times", "deccan herald", "free press journal",
    "asianet", "news18", "india today", "zee news", "republic",
    "moneycontrol", "the print", "scroll", "outlook", "the wire",
    "business standard", "dna india", "mid-day", "abp", "tv9", "aaj tak",
    "bloomberg", "financial times", "wall street journal", "washington post",
    "new york times", "sky news", "cnbc", "forbes", "politico",
]

_STOPWORDS = {
    "a", "an", "the", "in", "on", "at", "of", "to", "and", "for", "is", "are",
    "was", "were", "after", "over", "with", "from", "by", "as", "its", "it",
    "this", "that", "can", "will", "be", "or", "but", "not", "no", "yes",
    "how", "what", "when", "where", "why", "who", "which", "do", "does",
    "did", "has", "have", "had", "their", "they", "them", "his", "her",
    "new", "says", "said",
}

SIMILARITY_THRESHOLD = 0.22  # slightly lower for question-style headlines
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "").strip()
NEWSAPI_URL = "https://newsapi.org/v2/everything"


def _normalize_source(name: str) -> str:
    s = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower())
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _tokenize(text: str) -> set:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def _similarity(a: str, b: str) -> float:
    """Token-overlap (Jaccard) similarity."""
    tokens_a, tokens_b = _tokenize(a), _tokenize(b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def _is_trusted(source_name: str) -> bool:
    norm = _normalize_source(source_name)
    if not norm:
        return False
    for name in TRUSTED_SOURCE_NAMES:
        if name in norm or norm in name:
            return True
    return False


def _build_search_query(headline: str) -> str:
    """
    Build a better search query from a long / question-style headline.
    Prefer concrete nouns & key phrases over full sentence.
    """
    h = (headline or "").strip()
    # Remove OCR tags
    h = re.sub(r"^\[(?:tesseract|gemini-vision|easyocr|gemini)\]\s*", "", h, flags=re.I)
    # Drop leading numbers / punctuation noise
    h = re.sub(r"^[\d%\s.:\-–—]+", "", h).strip()

    # If short enough, use as-is
    if len(h) <= 90:
        return h

    # Extract important tokens and rebuild a shorter query
    tokens = [w for w in re.findall(r"[A-Za-z0-9%]+", h) if w.lower() not in _STOPWORDS and len(w) > 2]
    # Keep first ~8-10 meaningful words
    short = " ".join(tokens[:10])
    return short if short else h[:90]


def _search_newsapi(query: str, limit: int = 25):
    if not NEWSAPI_KEY:
        return None
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
            timeout=10,
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
        return None


def _search_google_news(query: str, limit: int = 25):
    url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        feed = feedparser.parse(url)
        results = []
        for entry in feed.entries[:limit]:
            source_name = ""
            if hasattr(entry, "source") and getattr(entry.source, "title", None):
                source_name = entry.source.title
            # Google sometimes puts source at end of title: ".... - The Hindu"
            title = entry.get("title", "")
            if not source_name and " - " in title:
                parts = title.rsplit(" - ", 1)
                if len(parts) == 2 and len(parts[1]) < 40:
                    title, source_name = parts[0].strip(), parts[1].strip()
            results.append({"title": title, "source": source_name})
        return results
    except Exception:
        return []


def verify_headline(headline: str) -> dict:
    """
    Search live news for corroboration from trusted outlets.

    Returns:
    {
        "verified": bool,
        "matched_sources": [{"title", "source", "similarity"}, ...],
        "num_checked": int,
        "provider": str,
        "query_used": str,
        "error": bool,
    }
    """
    headline = (headline or "").strip()
    if not headline:
        return {
            "verified": False,
            "matched_sources": [],
            "num_checked": 0,
            "provider": None,
            "query_used": "",
            "error": False,
        }

    query = _build_search_query(headline)
    provider = "newsapi"
    results = _search_newsapi(query)

    if not results:
        provider = "google_news_rss"
        results = _search_google_news(query)

    # Second try with a shorter / alternate query if first returned nothing useful
    if not results and len(query) > 40:
        # Take first 5-6 content words
        alt = " ".join(list(_tokenize(headline))[:6])
        if alt and alt != query:
            results = _search_google_news(alt) or _search_newsapi(alt) or []
            if results:
                query = alt
                provider = "google_news_rss"

    matched_sources = []
    for r in (results or []):
        sim = _similarity(headline, r["title"])
        # Also accept if a large chunk of key tokens from the query appear
        if sim < SIMILARITY_THRESHOLD:
            q_tokens = _tokenize(query)
            t_tokens = _tokenize(r["title"])
            if q_tokens and len(q_tokens & t_tokens) >= min(3, len(q_tokens)):
                sim = max(sim, 0.25)

        if sim >= SIMILARITY_THRESHOLD and _is_trusted(r["source"]):
            matched_sources.append({
                "title": r["title"],
                "source": r["source"],
                "similarity": round(sim, 2),
            })

    # Sort best matches first
    matched_sources.sort(key=lambda x: x["similarity"], reverse=True)

    return {
        "verified": len(matched_sources) > 0,
        "matched_sources": matched_sources[:8],
        "num_checked": len(results or []),
        "provider": provider,
        "query_used": query,
        "error": False,
    }
