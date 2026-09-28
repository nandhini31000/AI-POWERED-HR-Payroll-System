"""
gemini_helper.py
-----------------
Thin wrapper around the Google Gemini API used by the AI Payroll Assistant.

Kept deliberately small and defensive: any failure here (missing/invalid
API key, network issue, quota error, etc.) is caught and turned into a
friendly string instead of raising, so a Gemini outage never crashes the
Flask request or leaves a broken page for the user.
"""

import os
from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-flash-latest")

_client = None
_client_error = None

if API_KEY:
    try:
        _client = genai.Client(api_key=API_KEY)
    except Exception as exc:  # pragma: no cover - defensive
        _client_error = str(exc)
else:
    _client_error = "GEMINI_API_KEY is not set in the environment (.env)."


def ask_gemini(prompt, model=None):
    """
    Send `prompt` to Gemini and return the plain-text reply.

    Never raises: on any failure it returns a short, user-safe message so
    the chatbot always responds instead of showing a 500 error page.
    """

    if _client is None:
        return (
            "⚠️ The AI Assistant is not configured correctly on the server "
            f"({_client_error}). Please ask your administrator to check "
            "GEMINI_API_KEY in the .env file."
        )

    if not prompt or not prompt.strip():
        return "Please ask a question so I can help."

    try:
        response = _client.models.generate_content(
            model=model or MODEL_NAME,
            contents=prompt,
        )

        text = getattr(response, "text", None)

        if not text:
            return "I couldn't generate a response for that. Could you rephrase your question?"

        return text.strip()

    except genai_errors.APIError as exc:
        return f"⚠️ The AI service returned an error ({exc}). Please try again in a moment."

    except Exception as exc:  # pragma: no cover - network/timeout/etc.
        return f"⚠️ I couldn't reach the AI service right now ({exc}). Please try again shortly."
