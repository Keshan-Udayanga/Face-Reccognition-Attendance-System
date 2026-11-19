import json
import os
from datetime import date
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
ROUTER_INSTRUCTION = (
    "Classify the latest user request for the SmartFace attendance application, "
    "using earlier user messages only as context. "
    "Choose only the data sources needed: csv for attendance records, database "
    "for employee records, or both when the request needs both. For general "
    "application questions, choose no sources and use intent 'general'. "
    "Return only JSON with keys sources, intent, employee_id, employee_name, "
    "and date. sources must contain only 'csv' and/or 'database'. intent must "
    "be one of attendance_records, attendance_summary, employee_records, "
    "employee_summary, combined, or general. Put missing filters as null. "
    "Convert requested dates to YYYY-MM-DD. Do not answer the user and do not "
    "request or include database or attendance records."
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


def generate_data_request_plan(messages: Sequence[tuple[str, str]]) -> dict[str, object]:
    """Ask Gemini to choose data agents without sending any agent data to it."""
    load_dotenv()
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not api_key:
        raise GeminiConfigurationError(
            "GEMINI_API_KEY is not configured in the backend environment."
        )

    user_messages = [text for role, text in messages if role == "user"]
    if not user_messages:
        raise GeminiResponseError("A user message is required to route a chat request.")

    # Exclude assistant replies so earlier locally returned records never reach Gemini.
    conversation = "\n".join(
        [f"Current date: {date.today().isoformat()}"]
        + [f"User: {text}" for text in user_messages]
    )
    response = _client_for_key(api_key).models.generate_content(
        model=os.getenv("GEMINI_MODEL", MODEL_NAME),
        contents=conversation,
        config=types.GenerateContentConfig(
            system_instruction=ROUTER_INSTRUCTION,
            response_mime_type="application/json",
        ),
    )

    if not response.text or not response.text.strip():
        raise GeminiResponseError("Gemini returned an empty routing response.")

    try:
        plan = json.loads(response.text)
    except json.JSONDecodeError as error:
        raise GeminiResponseError("Gemini returned an invalid routing response.") from error

    if not isinstance(plan, dict):
        raise GeminiResponseError("Gemini returned an invalid routing response.")

    sources = plan.get("sources")
    allowed_sources = {"csv", "database"}
    if (
        not isinstance(sources, list)
        or any(not isinstance(source, str) or source not in allowed_sources for source in sources)
    ):
        raise GeminiResponseError("Gemini selected an unsupported data source.")

    allowed_intents = {
        "attendance_records",
        "attendance_summary",
        "employee_records",
        "employee_summary",
        "combined",
        "general",
    }
    intent = plan.get("intent")
    if not isinstance(intent, str) or intent not in allowed_intents:
        raise GeminiResponseError("Gemini returned an unsupported request type.")

    employee_id = plan.get("employee_id")
    if employee_id is not None and (
        isinstance(employee_id, bool) or not isinstance(employee_id, (str, int))
    ):
        raise GeminiResponseError("Gemini returned an invalid employee ID filter.")

    employee_name = plan.get("employee_name")
    if employee_name is not None and not isinstance(employee_name, str):
        raise GeminiResponseError("Gemini returned an invalid employee name filter.")

    requested_date = plan.get("date")
    if requested_date is not None and not isinstance(requested_date, str):
        raise GeminiResponseError("Gemini returned an invalid date filter.")
    if requested_date is not None:
        try:
            requested_date = date.fromisoformat(requested_date).isoformat()
        except ValueError as error:
            raise GeminiResponseError("Gemini returned an invalid date filter.") from error

    return {
        "sources": list(dict.fromkeys(sources)),
        "intent": intent,
        "employee_id": str(employee_id).strip() if employee_id is not None else None,
        "employee_name": employee_name.strip() if employee_name else None,
        "date": requested_date,
    }
