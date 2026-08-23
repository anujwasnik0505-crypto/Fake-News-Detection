"""
Rule-based "implausibility check" — catches common fake-news red flags that a
style-based ML/DL model can miss (e.g. a formally-worded but factually absurd claim).
This is a heuristic supplement, not a replacement for the model or verification —
real fake-news systems commonly combine rule-based signals with ML for exactly
this reason: style-based models can be fooled by well-written implausible claims.
"""
import re

# Sweeping/absolute claims are a common fake-news pattern — real policy changes are
# almost never framed as instant, universal, and unconditional.
ABSOLUTE_PATTERNS = [
    r"\ball\b.*\b(citizens|people|students|users)\b",
    r"\bevery(one|body)?\b",
    r"\bno\s+application\s+needed\b",
    r"\bstarting\s+tomorrow\b",
    r"\beffective\s+immediately\b",
    r"\boutlawed\b|\bbanned\b|\bofficially\s+bans?\b",
    r"\bonly\s+official\b",
    r"\bmandatory\s+for\s+all\b",
    r"\bfree\s+(smartphones?|money|cars?|houses?)\s+for\s+all\b",
    r"\b100%\s+(free|guaranteed)\b",
    r"\bsecret\s+(government|plan|program)\b",
    r"\bwill\s+disappear\b|\bwill\s+cease\s+to\s+exist\b",
    r"\bnasa\s+(confirms|warns|issues\s+emergency)\b",
    r"\bscientists?\s+confirm(s)?\b.*\b(forever|permanently|never)\b",
]

# Overly dramatic phrasing is another common tell, though weaker on its own.
SENSATIONAL_WORDS = [
    "shocking", "unbelievable", "you won't believe", "emergency warning",
    "breaking:", "urgent:", "must read", "share before it's deleted",
]


def check_plausibility(headline):
    """Flag common implausibility/red-flag patterns in a headline.

    Returns: {"flagged": bool, "matched_patterns": [str, ...]}
    This is a supplementary signal — a flagged headline is not proof of anything,
    it just means the wording matches patterns common in fabricated claims.
    """
    text = headline.lower()
    matched = []

    for pattern in ABSOLUTE_PATTERNS:
        if re.search(pattern, text):
            matched.append(pattern)

    for word in SENSATIONAL_WORDS:
        if word in text:
            matched.append(word)

    return {"flagged": len(matched) > 0, "matched_patterns": matched}
