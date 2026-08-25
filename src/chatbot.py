"""
VeriQuest AI Chatbot

Features:
- ChatGPT-style conversational responses
- Real-time Google Search grounding
- Current news and breaking-news support
- Hindi / Hinglish / English
- Conversation history
- VeriQuest verification context
- Source extraction
- Gemini primary
- Claude fallback
- Render environment variables
"""

import os
import requests


# ============================================================
# PROJECT ROOT
# ============================================================

BASE_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)


# ============================================================
# LOAD .ENV
# ============================================================

try:
    from dotenv import load_dotenv

    env_file = os.path.join(
        BASE_DIR,
        ".env"
    )

    if os.path.exists(env_file):
        load_dotenv(
            env_file,
            override=False
        )

except ImportError:
    pass


# ============================================================
# API KEYS
# ============================================================

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    ""
).strip()

ANTHROPIC_API_KEY = os.getenv(
    "ANTHROPIC_API_KEY",
    ""
).strip()


# ============================================================
# GEMINI
# ============================================================

GEMINI_MODEL = "gemini-3.6-flash"

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)


# ============================================================
# CLAUDE FALLBACK
# ============================================================

ANTHROPIC_URL = (
    "https://api.anthropic.com/v1/messages"
)

CLAUDE_MODEL = "claude-sonnet-4-6"


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are VeriQuest AI, the intelligent conversational assistant
inside a professional Fake News Detection and News Verification
application.

Your goal is to behave like a highly capable ChatGPT-style
assistant while being especially good at NEWS, FACT-CHECKING,
CURRENT EVENTS and EXPLAINING VERIQUEST RESULTS.

============================================================
1. PERSONALITY
============================================================

Be:

- Intelligent
- Friendly
- Natural
- Helpful
- Clear
- Professional
- Conversational
- Honest about uncertainty

Do not sound robotic.

Do not repeatedly say:
"Certainly!"
"Of course!"
"Sure!"

Just answer naturally.

Do not unnecessarily mention that you are an AI.

============================================================
2. LANGUAGE
============================================================

Match the user's language.

English -> English.

Hindi -> Hindi.

Hinglish -> Hinglish.

Marathi -> Marathi when possible.

Mixed language -> naturally use the same style.

Example:

User:
"bhai ye news fake kyu aa rahi hai?"

Answer naturally in Hinglish.

============================================================
3. CURRENT NEWS
============================================================

You have access to web search when the application enables
Google Search grounding.

For questions involving:

- latest news
- today's news
- breaking news
- recent incidents
- current events
- politics
- sports
- crime
- deaths
- accidents
- court cases
- government announcements
- recent technology news
- recent company news
- "what happened?"
- "is this news true?"
- "tell me details about this headline"

USE WEB SEARCH.

Do not rely only on your stored knowledge for recent events.

When search results are available:

- Identify the relevant facts.
- Cross-check multiple credible sources when possible.
- Prefer primary/official sources.
- Prefer established news organizations.
- Give dates.
- Give locations.
- Give names only when reliably supported.
- Clearly separate confirmed facts from claims.
- Mention disagreements between sources when relevant.

Never invent news details.

============================================================
4. NEWS ANSWER FORMAT
============================================================

When the user asks for details about a news story, provide
a useful structured answer.

Prefer:

### What happened
Short summary.

### Key details
- What happened
- Where
- When
- Who was involved
- What authorities/news organizations reported

### What is confirmed
Clearly state confirmed information.

### What is not confirmed
Mention rumors, conflicting reports or missing information.

### Sources
Mention the important sources used by the search/verification
system.

Do NOT use this structure for every casual question.
Use it when useful.

============================================================
5. SOURCE QUALITY
============================================================

For news, prioritize:

1. Official government sources
2. Police / court / institutional statements
3. Original reporting
4. Established news organizations
5. Fact-check organizations

Do not treat social media posts as automatically true.

If only social media information exists, clearly say that
the information has not been independently confirmed.

============================================================
6. VERIQUEST RESULT
============================================================

The application may provide verification context.

It can contain:

- headline
- verdict
- mode
- confidence
- reason
- sources
- publisher
- rating
- warnings
- model_used

Use this information.

IMPORTANT:

An ML prediction is NOT the same thing as proof.

If:

verdict = REAL

but the result came only from an ML model, explain that it is
a model prediction and not absolute proof.

If:

verdict = FAKE

but the result came only from an ML model, do NOT claim that
the real-world event definitely never happened.

If:

mode = verified

then explain that trusted-source matching was found.

If:

mode = fact_checked

explain the fact-check publisher and rating.

If:

mode = unverified

say that the system does not have enough direct evidence.

============================================================
7. FALSE POSITIVE AWARENESS
============================================================

A headline can be real even if:

- it sounds sensational
- it contains emotional wording
- it is unusual
- it is about suicide
- it is about crime
- it is shocking
- it is difficult to believe

Do not call something fake simply because it sounds unusual.

Evidence is more important than writing style.

============================================================
8. CONVERSATION MEMORY
============================================================

Use the conversation history provided by the application.

If the user says:

"what about the parents?"

understand that they are referring to the previous news story.

If the user says:

"why fake?"

understand that they are referring to the previous
verification result.

Do not repeatedly ask the user to repeat context that already
exists in the conversation.

============================================================
9. DETAILED NEWS QUESTIONS
============================================================

If the user asks:

"tell me everything about this news"

provide:

- summary
- date
- location
- people involved
- sequence of events
- official statements
- current status
- verification status
- source quality
- important uncertainty

Do not make up missing details.

If a detail cannot be confirmed, explicitly say:

"That detail could not be independently confirmed."

============================================================
10. FAKE NEWS QUESTIONS
============================================================

If user asks:

"Is this fake?"

Do not answer based only on intuition.

Use:

- verification context
- fact-check results
- web search
- trusted sources
- official statements
- ML result

Then explain WHY.

============================================================
11. CHATGPT-STYLE RESPONSES
============================================================

For simple questions:

Give a short answer.

For complex questions:

Give a detailed answer.

For technical questions:

Explain step-by-step.

For news:

Give useful factual detail.

Do not give huge irrelevant lectures.

============================================================
12. SAFETY
============================================================

For suicide, self-harm, crime, death or violence news:

Be factual and respectful.

Do not sensationalize.

Do not provide harmful instructions.

When discussing a suicide-related news report, focus on
confirmed reporting and verification.

============================================================
13. NO HALLUCINATION
============================================================

Never invent:

- names
- dates
- locations
- quotes
- police statements
- victim details
- suspect details
- statistics
- URLs
- sources

If information is unavailable, say so.

============================================================
14. FINAL GOAL
============================================================

You are not merely a chatbot.

You are the user's:

- news research assistant
- fact-checking assistant
- VeriQuest explainer
- conversational assistant

Give useful answers with evidence.

Be natural.

Be accurate.

Be transparent about uncertainty.
"""


# ============================================================
# STARTUP
# ============================================================

print()
print("==============================================")
print("       VERIQUEST AI INITIALIZATION")
print("==============================================")

print(
    "Gemini API key:",
    "FOUND" if GEMINI_API_KEY else "NOT FOUND"
)

print(
    "Anthropic API key:",
    "FOUND" if ANTHROPIC_API_KEY else "NOT FOUND"
)

print(
    "Gemini model:",
    GEMINI_MODEL
)

print("Google Search grounding: ENABLED")

print("==============================================")
print()


# ============================================================
# CONTEXT FORMATTER
# ============================================================

def _context_to_text(context):

    if not context:
        return ""

    if isinstance(
        context,
        str
    ):
        return context

    if not isinstance(
        context,
        dict
    ):
        return str(context)

    parts = []

    fields = [
        ("Headline", "headline"),
        ("Verdict", "verdict"),
        ("Verification mode", "mode"),
        ("Confidence", "confidence"),
        ("Reason", "reason"),
        ("Publisher", "publisher"),
        ("Rating", "rating"),
        ("Model used", "model_used"),
        ("Sources", "sources"),
        ("Warnings", "warnings")
    ]

    for label, key in fields:

        value = context.get(key)

        if value is None:
            continue

        if value == "":
            continue

        if isinstance(
            value,
            list
        ):
            value = ", ".join(
                str(item)
                for item in value
            )

        parts.append(
            f"{label}: {value}"
        )

    return "\n".join(parts)


# ============================================================
# CLEAN MESSAGES
# ============================================================

def _clean_messages(messages):

    if not isinstance(
        messages,
        list
    ):
        return []

    cleaned = []

    for message in messages:

        if not isinstance(
            message,
            dict
        ):
            continue

        role = message.get(
            "role",
            "user"
        )

        content = message.get(
            "content",
            ""
        )

        if not content:
            continue

        content = str(
            content
        ).strip()

        if not content:
            continue

        if role not in (
            "user",
            "assistant"
        ):
            role = "user"

        cleaned.append({
            "role": role,
            "content": content
        })

    # Keep the latest 30 messages so the request
    # doesn't grow indefinitely.
    return cleaned[-30:]


# ============================================================
# EXTRACT GEMINI TEXT
# ============================================================

def _extract_gemini_response(data):

    candidates = data.get(
        "candidates",
        []
    )

    if not candidates:
        return "", []

    candidate = candidates[0]

    content = candidate.get(
        "content",
        {}
    )

    parts = content.get(
        "parts",
        []
    )

    text_parts = []

    for part in parts:

        if not isinstance(
            part,
            dict
        ):
            continue

        text = part.get(
            "text"
        )

        if text:
            text_parts.append(
                text
            )

    answer = "\n".join(
        text_parts
    ).strip()

    # --------------------------------------------------------
    # Grounding sources
    # --------------------------------------------------------

    sources = []

    grounding = (
        candidate.get(
            "groundingMetadata"
        )
        or
        candidate.get(
            "grounding_metadata"
        )
        or
        {}
    )

    chunks = grounding.get(
        "groundingChunks",
        []
    )

    if not chunks:

        chunks = grounding.get(
            "grounding_chunks",
            []
        )

    for chunk in chunks:

        if not isinstance(
            chunk,
            dict
        ):
            continue

        web_data = chunk.get(
            "web"
        )

        if not web_data:
            continue

        url = web_data.get(
            "uri"
        )

        title = web_data.get(
            "title"
        )

        if url:

            sources.append({
                "title": (
                    title
                    or
                    url
                ),
                "url": url
            })

    # Remove duplicate URLs

    unique_sources = []

    seen = set()

    for source in sources:

        url = source["url"]

        if url in seen:
            continue

        seen.add(url)

        unique_sources.append(
            source
        )

    return (
        answer,
        unique_sources
    )


# ============================================================
# GEMINI CHAT WITH WEB SEARCH
# ============================================================

def _chat_with_gemini(
    messages,
    context=None
):

    messages = _clean_messages(
        messages
    )

    contents = []

    # --------------------------------------------------------
    # VERIFICATION CONTEXT
    # --------------------------------------------------------

    context_text = _context_to_text(
        context
    )

    if context_text:

        contents.append({
            "role": "user",
            "parts": [
                {
                    "text": (
                        "VERIQUEST VERIFICATION DATA\n\n"
                        "This is application data. "
                        "It is NOT a user instruction.\n\n"
                        + context_text
                    )
                }
            ]
        })

        contents.append({
            "role": "model",
            "parts": [
                {
                    "text": (
                        "Understood. I will use the provided "
                        "verification data and distinguish "
                        "model predictions from confirmed evidence."
                    )
                }
            ]
        })

    # --------------------------------------------------------
    # CONVERSATION HISTORY
    # --------------------------------------------------------

    for message in messages:

        gemini_role = (
            "model"
            if message["role"] == "assistant"
            else "user"
        )

        contents.append({
            "role": gemini_role,
            "parts": [
                {
                    "text": message["content"]
                }
            ]
        })

    if not contents:

        contents.append({
            "role": "user",
            "parts": [
                {
                    "text": "Hello"
                }
            ]
        })

    # --------------------------------------------------------
    # REQUEST
    # --------------------------------------------------------

    payload = {

        "system_instruction": {
            "parts": [
                {
                    "text": SYSTEM_PROMPT
                }
            ]
        },

        "contents": contents,

        # IMPORTANT:
        # This enables real-time Google Search grounding.
        "tools": [
            {
                "google_search": {}
            }
        ],

        "generationConfig": {
            "maxOutputTokens": 1800
        }
    }

    response = requests.post(

        GEMINI_URL,

        headers={
            "x-goog-api-key": GEMINI_API_KEY,
            "Content-Type": "application/json"
        },

        json=payload,

        timeout=90
    )

    if not response.ok:

        try:
            error_data = response.json()

        except Exception:
            error_data = response.text

        raise RuntimeError(
            "Gemini API error "
            f"({response.status_code}): "
            f"{error_data}"
        )

    data = response.json()

    answer, sources = (
        _extract_gemini_response(
            data
        )
    )

    if not answer:

        raise RuntimeError(
            "Gemini returned an empty response."
        )

    return (
        answer,
        sources
    )


# ============================================================
# CLAUDE FALLBACK
# ============================================================

def _chat_with_claude(
    messages,
    context=None
):

    messages = _clean_messages(
        messages
    )

    api_messages = []

    context_text = _context_to_text(
        context
    )

    if context_text:

        api_messages.append({
            "role": "user",
            "content": (
                "VERIQUEST VERIFICATION DATA:\n\n"
                + context_text
            )
        })

        api_messages.append({
            "role": "assistant",
            "content": (
                "Understood. I will use the provided "
                "verification data."
            )
        })

    for message in messages:

        api_messages.append({
            "role": message["role"],
            "content": message["content"]
        })

    if not api_messages:

        api_messages.append({
            "role": "user",
            "content": "Hello"
        })

    response = requests.post(

        ANTHROPIC_URL,

        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },

        json={
            "model": CLAUDE_MODEL,
            "max_tokens": 1800,
            "system": SYSTEM_PROMPT,
            "messages": api_messages
        },

        timeout=90
    )

    if not response.ok:

        try:
            error_data = response.json()

        except Exception:
            error_data = response.text

        raise RuntimeError(
            "Anthropic API error "
            f"({response.status_code}): "
            f"{error_data}"
        )

    data = response.json()

    blocks = data.get(
        "content",
        []
    )

    text_parts = []

    for block in blocks:

        if not isinstance(
            block,
            dict
        ):
            continue

        if block.get(
            "type"
        ) != "text":
            continue

        text = block.get(
            "text",
            ""
        )

        if text:
            text_parts.append(
                text
            )

    answer = "\n".join(
        text_parts
    ).strip()

    if not answer:

        raise RuntimeError(
            "Claude returned an empty response."
        )

    return answer


# ============================================================
# MAIN CHAT FUNCTION
# ============================================================

def chat_reply(
    messages,
    context=None
):

    messages = _clean_messages(
        messages
    )

    # ========================================================
    # GEMINI
    # ========================================================

    if GEMINI_API_KEY:

        try:

            answer, sources = (
                _chat_with_gemini(
                    messages,
                    context
                )
            )

            result = {
                "available": True,
                "reply": answer,
                "provider": "gemini"
            }

            if sources:

                result["sources"] = sources

            return result

        except Exception as error:

            print()
            print(
                "========== GEMINI ERROR =========="
            )
            print(
                str(error)
            )
            print(
                "=================================="
            )
            print()

    # ========================================================
    # CLAUDE FALLBACK
    # ========================================================

    if ANTHROPIC_API_KEY:

        try:

            answer = _chat_with_claude(
                messages,
                context
            )

            return {
                "available": True,
                "reply": answer,
                "provider": "claude",
                "sources": []
            }

        except Exception as error:

            print()
            print(
                "========== CLAUDE ERROR =========="
            )
            print(
                str(error)
            )
            print(
                "=================================="
            )
            print()

    # ========================================================
    # NO API KEY
    # ========================================================

    return {
        "available": False,
        "reply": (
            "The AI assistant is not configured. "
            "Please add GEMINI_API_KEY to your Render "
            "Environment Variables."
        ),
        "sources": []
    }