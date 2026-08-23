"""
Google Fact Check Tools API — searches whether a headline/claim has already
been reviewed by professional fact-checkers (PolitiFact, Alt News, Snopes, etc.)
Free tier, needs a Google Cloud API key with the "Fact Check Tools API" enabled.
Get one at: https://console.cloud.google.com/apis/library/factchecktools.googleapis.com
"""
import os
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

FACTCHECK_API_KEY = os.environ.get("GOOGLE_FACTCHECK_API_KEY", "")
FACTCHECK_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"


def search_fact_checks(headline, limit=5):
    """
    Search existing fact-checks for a claim similar to this headline.

    Returns: {"found": bool, "reviews": [{"claim": str, "rating": str, "publisher": str, "url": str}]}
    Returns {"found": False, "reviews": [], "configured": False} if no API key is set.
    """
    if not FACTCHECK_API_KEY:
        return {"found": False, "reviews": [], "configured": False}

    try:
        resp = requests.get(
            FACTCHECK_URL,
            params={"query": headline, "pageSize": limit, "key": FACTCHECK_API_KEY},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return {"found": False, "reviews": [], "configured": True, "error": True}

    reviews = []
    for claim in data.get("claims", []):
        text = claim.get("text", "")
        for review in claim.get("claimReview", []):
            reviews.append({
                "claim": text,
                "rating": review.get("textualRating", "Unrated"),
                "publisher": review.get("publisher", {}).get("name", "Unknown"),
                "url": review.get("url", ""),
            })

    return {"found": len(reviews) > 0, "reviews": reviews, "configured": True, "error": False}
