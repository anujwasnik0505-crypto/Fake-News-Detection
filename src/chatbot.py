"""
Conversational AI assistant for the Fake News Detection web UI.

Features:
- Natural conversation: hey, hello, thanks, etc.
- Explains verification results
- Explains the 5-layer fake-news detection pipeline
- Explains confidence scores
- Discusses misinformation and media literacy
- Uses Gemini first
- Uses Claude as fallback if configured
- Loads API keys from project-root .env
"""

import os
import requests


# ============================================================
# LOAD .ENV
# ============================================================

try:
    from dotenv import load_dotenv

    # chatbot.py:
    # project/
    # ├── .env
    # └── src/
    #     └── chatbot.py

    BASE_DIR = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            ".."
        )
    )

    ENV_FILE = os.path.join(
        BASE_DIR,
        ".env"
    )

    load_dotenv(ENV_FILE)

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

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/gemini-3.6-flash:generateContent"
)


# ============================================================
# ANTHROPIC
# ============================================================

ANTHROPIC_URL = (
    "https://api.anthropic.com/v1/messages"
)


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are VeriQuest, the friendly AI assistant inside a
fake-news and misinformation verification website.

Your purpose is to help users understand:

- Fake-news detection
- Headline verification
- Verification results
- REAL / FAKE / UNVERIFIED verdicts
- Confidence scores
- Fact-checking
- AI analysis
- Machine-learning predictions
- Misinformation
- Media literacy
- How the verification pipeline works

The website uses a five-layer verification pipeline:

1. Live trusted-source verification using news sources and RSS
2. Professional fact-check databases
3. Rule-based fake-news red-flag detection
4. LLM-based plausibility analysis
5. Trained ML/DL model as the final fallback

IMPORTANT CONVERSATION RULES:

1. Be a normal conversational assistant.

2. If the user says:
   - hey
   - heyy
   - hello
   - hi
   - good morning
   - what's up

   respond naturally and briefly.

   Example:
   "Hey! 👋 How can I help you today?"

3. Do NOT immediately explain the entire fake-news system
   when the user only says "hey".

4. If the user asks:
   "how does this work?"
   explain the verification pipeline simply.

5. If the user asks about a headline that was just checked,
   use the verification context supplied by the application.

6. Never invent sources, evidence, fact-checkers, or verification
   results.

7. Do not claim that something is definitely true or false unless
   the supplied verification information supports that conclusion.

8. Be honest about uncertainty.

9. Keep normal responses short, around 2-5 sentences.

10. If the user asks for detailed information, give a detailed answer.

11. Use simple language.

12. Be friendly, professional, and helpful.

13. The assistant is an explanation/helper tool. It does not replace
    professional fact-checking or reliable primary sources.
"""


# ============================================================
# STARTUP STATUS
# ============================================================

print()
print("==============================================")
print("        VERIQUEST CHATBOT INITIALIZATION")
print("==============================================")

if GEMINI_API_KEY:
    print("Gemini API key: FOUND")
else:
    print("Gemini API key: NOT FOUND")

if ANTHROPIC_API_KEY:
    print("Anthropic API key: FOUND")
else:
    print("Anthropic API key: NOT FOUND")

print("==============================================")
print()


# ============================================================
# CONTEXT FORMATTER
# ============================================================

def _context_to_text(context):
    """
    Converts verification context into readable text.
    """

    if not context:
        return ""

    if isinstance(context, str):
        return context

    if isinstance(context, dict):

        parts = []

        headline = context.get("headline")
        verdict = context.get("verdict")
        mode = context.get("mode")
        confidence = context.get("confidence")
        reason = context.get("reason")
        publisher = context.get("publisher")
        rating = context.get("rating")
        sources = context.get("sources")

        if headline:
            parts.append(
                f"Headline: {headline}"
            )

        if verdict:
            parts.append(
                f"Verdict: {verdict}"
            )

        if mode:
            parts.append(
                f"Verification mode: {mode}"
            )

        if confidence is not None:
            parts.append(
                f"Model confidence: {confidence}"
            )

        if reason:
            parts.append(
                f"Reason: {reason}"
            )

        if publisher:
            parts.append(
                f"Fact-check publisher: {publisher}"
            )

        if rating:
            parts.append(
                f"Fact-check rating: {rating}"
            )

        if sources:

            if isinstance(sources, list):
                sources_text = ", ".join(
                    str(source)
                    for source in sources
                )
            else:
                sources_text = str(sources)

            parts.append(
                f"Trusted sources: {sources_text}"
            )

        return "\n".join(parts)

    return str(context)


# ============================================================
# GEMINI CHAT
# ============================================================

def _chat_with_gemini(
    messages,
    context=None
):
    """
    Sends conversation to Gemini.
    """

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
                    "text":
                        "The following is the verification context "
                        "from the website. Use it only when relevant.\n\n"
                        "VERIFICATION CONTEXT:\n"
                        + context_text
                }
            ]

        })

        contents.append({

            "role": "model",

            "parts": [
                {
                    "text":
                        "Understood. I will use the verification "
                        "context when it is relevant."
                }
            ]

        })


    # --------------------------------------------------------
    # CHAT HISTORY
    # --------------------------------------------------------

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

        if role == "assistant":
            gemini_role = "model"
        else:
            gemini_role = "user"

        contents.append({

            "role": gemini_role,

            "parts": [
                {
                    "text": str(content)
                }
            ]

        })


    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

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
    # REQUEST BODY
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

        "generationConfig": {

            "temperature": 0.7,

            "maxOutputTokens": 500

        }

    }


    # --------------------------------------------------------
    # REQUEST
    # --------------------------------------------------------

    response = requests.post(

        GEMINI_URL,

        headers={

            "x-goog-api-key":
                GEMINI_API_KEY,

            "Content-Type":
                "application/json"

        },

        json=payload,

        timeout=30

    )


    # --------------------------------------------------------
    # ERROR
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    data = response.json()


    candidates = data.get(
        "candidates",
        []
    )

    if not candidates:

        raise RuntimeError(
            f"Gemini returned no candidates: {data}"
        )


    content = candidates[0].get(
        "content",
        {}
    )

    parts = content.get(
        "parts",
        []
    )


    text_parts = []

    for part in parts:

        if isinstance(
            part,
            dict
        ):

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


    if not answer:

        raise RuntimeError(
            f"Gemini returned an empty response: {data}"
        )


    return answer


# ============================================================
# CLAUDE CHAT
# ============================================================

def _chat_with_claude(
    messages,
    context=None
):
    """
    Claude fallback.
    """

    api_messages = []


    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    context_text = _context_to_text(
        context
    )

    if context_text:

        api_messages.append({

            "role": "user",

            "content":
                "Verification context:\n\n"
                + context_text

        })

        api_messages.append({

            "role": "assistant",

            "content":
                "Understood. I will use the verification "
                "context when relevant."

        })


    # --------------------------------------------------------
    # HISTORY
    # --------------------------------------------------------

    for message in messages:

        if not isinstance(
            message,
            dict
        ):
            continue

        role = message.get(
            "role"
        )

        content = message.get(
            "content",
            ""
        )

        if role not in (
            "user",
            "assistant"
        ):
            continue

        if not content:
            continue

        api_messages.append({

            "role": role,

            "content": str(content)

        })


    if not api_messages:

        api_messages.append({

            "role": "user",

            "content": "Hello"

        })


    # --------------------------------------------------------
    # REQUEST
    # --------------------------------------------------------

    response = requests.post(

        ANTHROPIC_URL,

        headers={

            "x-api-key":
                ANTHROPIC_API_KEY,

            "anthropic-version":
                "2023-06-01",

            "content-type":
                "application/json"

        },

        json={

            "model":
                "claude-sonnet-4-6",

            "max_tokens":
                500,

            "system":
                SYSTEM_PROMPT,

            "messages":
                api_messages

        },

        timeout=30

    )


    # --------------------------------------------------------
    # ERROR
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    blocks = data.get(
        "content",
        []
    )

    text_parts = []

    for block in blocks:

        if (
            isinstance(block, dict)
            and block.get("type") == "text"
        ):

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
            f"Claude returned an empty response: {data}"
        )


    return answer


# ============================================================
# MAIN CHAT FUNCTION
# ============================================================

def chat_reply(
    messages,
    context=None
):
    """
    Main chatbot function.

    messages:
        [
            {
                "role": "user",
                "content": "hey"
            },
            {
                "role": "assistant",
                "content": "Hey! How can I help?"
            }
        ]

    context:
        Optional verification result.

    Returns:
        {
            "available": True/False,
            "reply": "..."
        }
    """

    # --------------------------------------------------------
    # VALIDATE
    # --------------------------------------------------------

    if not isinstance(
        messages,
        list
    ):
        messages = []


    # --------------------------------------------------------
    # GEMINI
    # --------------------------------------------------------

    if GEMINI_API_KEY:

        try:

            answer = _chat_with_gemini(

                messages,

                context

            )

            return {

                "available": True,

                "reply": answer

            }

        except Exception as error:

            print()
            print("========== GEMINI ERROR ==========")
            print(error)
            print("==================================")
            print()


    # --------------------------------------------------------
    # CLAUDE FALLBACK
    # --------------------------------------------------------

    if ANTHROPIC_API_KEY:

        try:

            answer = _chat_with_claude(

                messages,

                context

            )

            return {

                "available": True,

                "reply": answer

            }

        except Exception as error:

            print()
            print("========== CLAUDE ERROR ==========")
            print(error)
            print("==================================")
            print()

            return {

                "available": False,

                "reply":
                    "The AI assistant could not connect "
                    "to the AI service right now."

            }


    # --------------------------------------------------------
    # NO API KEY
    # --------------------------------------------------------

    return {

        "available": False,

        "reply":
            "The AI assistant is not configured. "
            "Please add GEMINI_API_KEY to your .env file."

    }