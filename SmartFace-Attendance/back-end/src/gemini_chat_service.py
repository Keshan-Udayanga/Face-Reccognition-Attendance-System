import os
from functools import lru_cache
from typing import Sequence

from dotenv import load_dotenv
from google import genai
from google.genai import types


MODEL_NAME = "gemini-3.5-flash-lite"
SYSTEM_INSTRUCTION = (
    "You are the SmartFace attendance application assistant. "
    "Answer clearly and helpfully about using the application. "
    "You do not have access to employee records or live attendance data."
)


class GeminiConfigurationError(Exception):
    pass


class GeminiResponseError(Exception):
    pass


@lru_cache(maxsize=1)
def _client_for_key(api_key: str):
    return genai.Client(api_key=api_key)


def generate_chat_reply(messages: Sequence[tuple[str, str]]) -> str:
    load_dotenv()
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not api_key:
        raise GeminiConfigurationError(
            "GEMINI_API_KEY is not configured in the backend environment."
        )

    conversation = "\n".join(
        f"{'User' if role == 'user' else 'Assistant'}: {text}"
        for role, text in messages
    )
    response = _client_for_key(api_key).models.generate_content(
        model=os.getenv("GEMINI_MODEL", MODEL_NAME),
        contents=conversation,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION),
    )

    if not response.text or not response.text.strip():
        raise GeminiResponseError("Gemini returned an empty response.")

    return response.text.strip()
