from datetime import date, datetime, timedelta
import logging
import re

import duckdb
import psycopg2
from google.genai.errors import APIError

from agents import csv_agent, database_agent
from src.gemini_chat_service import (
    GeminiConfigurationError,
    GeminiResponseError,
    generate_chat_reply,
    generate_data_request_plan,
)


class SupervisorDataError(Exception):
    """Raised when a selected data agent cannot retrieve its records."""


EMPLOYEE_FIELD_LABELS = {
    "employee_id": "Employee ID",
    "employee_name": "Employee name",
    "department": "Department",
    "designation": "Designation",
}
ATTENDANCE_FIELD_LABELS = {
    "employee_id": "Employee ID",
    "employee_name": "Employee name",
    "department": "Department",
    "designation": "Designation",
    "date": "Date",
    "check_in": "Check-in",
    "check_out": "Check-out",
    "total_hours": "Total hours",
}
HONORIFIC_TOKENS = {"mr", "mrs", "ms", "miss", "dr", "prof"}
LOCAL_QUERY_STOP_WORDS = {
    "a", "an", "and", "are", "came", "can", "come", "did", "do", "does",
    "employee", "employees", "for", "from", "get", "give", "has", "how", "in",
    "is", "it", "many", "me", "of", "on", "please", "show", "staff", "tell",
    "the", "their", "there", "to", "was", "were", "what", "when", "where", "which",
    "who", "yesterday", "today", "attendance", "attend", "attended", "attending",
    "present",
    "absent", "check", "checked", "in", "out", "date", "time", "hours",
    "total", "name", "details", "detail", "information", "designation",
    "department", "id", "count", "number", "record", "records", "of",
    "mr", "mrs", "ms", "miss",
    "dr", "prof", "s", "list", "all", "active", "any", "people", "person",
    "workers",
}
logger = logging.getLogger(__name__)


def _normalise_date(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()

    text = str(value).strip()
    for date_format in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, date_format).date().isoformat()
        except ValueError:
            continue
    return text


def _normalise_employee_name(value):
    # Ignore titles and punctuation so "Mr. Keshan" matches "Keshan Udayanga".
    return [
        token
        for token in re.findall(r"[^\W_]+", str(value).casefold())
        if token not in HONORIFIC_TOKENS
    ]


def _local_data_plan(user_text):
    """Build a narrow local plan for common data questions if Gemini is unavailable."""
    text = user_text.casefold()
    tokens = re.findall(r"[^\W_]+", text)
    name = " ".join(
        token
        for token in tokens
        if token not in LOCAL_QUERY_STOP_WORDS
        and token not in HONORIFIC_TOKENS
    )
    requested_date = None
    if "yesterday" in tokens:
        requested_date = (date.today() - timedelta(days=1)).isoformat()
    elif "today" in tokens:
        requested_date = date.today().isoformat()
    else:
        date_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", user_text)
        if date_match:
            requested_date = _normalise_date(date_match.group(0))

    asks_count = (
        "how many" in text
        or "number of" in text
        or bool(re.search(r"\bcount\b", text))
    )
    attendance_question = bool(
        re.search(
            r"\b(attendance|attend|attended|attending|present|absent|came|come|check[\s-]*in|check[\s-]*out)\b",
            text,
        )
    )

    if attendance_question:
        fields = []
        if asks_count:
            fields.append("count")
        asks_attendance_status = bool(
            name and re.search(r"\b(is|was|has|did|does)\b", text)
        )
        if asks_attendance_status:
            fields.append("attendance_status")
        if re.search(r"\bwho\b|\bname\b", text):
            fields.append("employee_name")
        if re.search(r"\bcheck[\s-]*in\b", text):
            fields.append("check_in")
        if re.search(r"\bcheck[\s-]*out\b", text):
            fields.append("check_out")
        if re.search(r"\btotal hours?\b|\bhours worked\b", text):
            fields.append("total_hours")
        if re.search(r"\bdate\b", text):
            fields.append("date")

        employee_fields = [
            field
            for field in ("department", "designation")
            if re.search(rf"\b{field}\b", text)
        ]
        fields.extend(employee_fields)
        if not fields and not name:
            return None
        sources = ["csv", "database"] if employee_fields else ["csv"]
        intent = (
            "combined"
            if employee_fields
            else "attendance_summary"
            if asks_count
            else "attendance_records"
        )
        return {
            "sources": sources,
            "intent": intent,
            "employee_id": None,
            "employee_name": name or None,
            "date": requested_date,
            "fields": list(dict.fromkeys(fields)),
        }

    employee_fields = []
    for field in ("designation", "department"):
        if re.search(rf"\b{field}\b", text):
            employee_fields.append(field)
    if re.search(r"\bemployee[\s_-]+id\b", text):
        employee_fields.append("employee_id")
    if re.search(r"\bname\b", text):
        employee_fields.append("employee_name")
    employee_question = bool(
        employee_fields
        or re.search(r"\b(employee|employees|staff|designation|department)\b", text)
    )
    if not employee_question:
        return None

    if asks_count:
        fields = ["count"]
        intent = "employee_summary"
    else:
        fields = employee_fields or ["employee_name"]
        intent = "employee_records"

    return {
        "sources": ["database"],
        "intent": intent,
        "employee_id": None,
        "employee_name": name or None,
        "date": None,
        "fields": fields,
    }


def _matches_filters(row, employee_id_key, employee_name_key, date_key, plan):
    requested_id = plan.get("employee_id")
    if requested_id and str(row.get(employee_id_key, "")).strip() != requested_id:
        return False

    requested_name = plan.get("employee_name")
    if requested_name:
        requested_tokens = _normalise_employee_name(requested_name)
        row_tokens = set(_normalise_employee_name(row.get(employee_name_key, "")))
        if not requested_tokens or not set(requested_tokens).issubset(row_tokens):
            return False

    requested_date = plan.get("date")
    if (
        requested_date
        and date_key
        and _normalise_date(row.get(date_key, "")) != requested_date
    ):
        return False

    return True


def _format_employee_reply(employees, intent, fields):
    if intent == "employee_summary":
        return f"There are {len(employees)} active employees in the database."

    if not employees:
        return "I couldn't find any active employees matching your request."

    record_fields = [
        field for field in fields if field in EMPLOYEE_FIELD_LABELS
    ]
    if not record_fields and "count" not in fields:
        return "Which employee information would you like to see?"

    lines = []
    for employee in employees[:10]:
        details = [
            f"{EMPLOYEE_FIELD_LABELS[field]}: {employee[field]}"
            for field in record_fields
            if employee.get(field) not in (None, "")
        ]
        if details:
            lines.append("- " + "; ".join(details))

    sections = []
    if "count" in fields:
        sections.append(f"Found {len(employees)} matching active employee(s).")
    if lines:
        sections.append("\n".join(lines))
    response = "\n".join(sections)
    if lines and len(employees) > len(lines):
        response += f"\nShowing {len(lines)} of {len(employees)} employees."
    return response


def _attendance_field_value(field, row, employee):
    values = {
        "employee_id": row.get("Employee ID"),
        "employee_name": employee.get("employee_name") or row.get("Employee Name"),
        "department": employee.get("department") or row.get("Departement"),
        "designation": employee.get("designation"),
        "date": row.get("Date"),
        "check_in": row.get("Check In"),
        "check_out": row.get("Check Out"),
        "total_hours": row.get("Total Hours"),
    }
    return values[field]


def _format_attendance_reply(rows, employees, intent, fields, plan=None):
    plan = plan or {}
    if not rows:
        if "attendance_status" in fields and plan.get("employee_name"):
            requested_date = plan.get("date") or "the requested date"
            return (
                f"No attendance record found for {plan['employee_name'].title()} "
                f"on {requested_date}."
            )
        return "I couldn't find attendance records matching your request."

    if "attendance_status" in fields:
        employee_by_id = {
            str(employee.get("employee_id")): employee
            for employee in employees or []
        }
        row = rows[0]
        employee = employee_by_id.get(str(row.get("Employee ID", "")), {})
        name = (
            employee.get("employee_name")
            or row.get("Employee Name")
            or plan.get("employee_name")
            or "The employee"
        )
        record_date = row.get("Date") or plan.get("date") or "the requested date"
        if any(str(record.get("Check In") or "").strip() for record in rows):
            return f"Yes. {name} has an attendance record for {record_date}."
        return (
            f"An attendance record was found for {name} on {record_date}, "
            "but no check-in time is recorded."
        )

    completed = sum(bool(str(row.get("Check Out") or "").strip()) for row in rows)
    if intent == "attendance_summary":
        summary_parts = []
        if "count" in fields:
            summary_parts.append(f"Found {len(rows)} attendance record(s).")
        if "checked_out_count" in fields:
            summary_parts.append(f"{completed} record(s) have a check-out.")
        if "open_count" in fields:
            summary_parts.append(
                f"{len(rows) - completed} record(s) do not have a check-out."
            )
        if summary_parts:
            return " ".join(summary_parts)

    employee_by_id = {
        str(employee.get("employee_id")): employee
        for employee in employees or []
    }
    record_fields = [
        field for field in fields if field in ATTENDANCE_FIELD_LABELS
    ]
    if not record_fields and "count" not in fields:
        return "Which attendance information would you like to see?"

    lines = []
    for row in rows[:10]:
        employee_id = str(row.get("Employee ID", ""))
        employee = employee_by_id.get(employee_id, {})
        details = [
            f"{ATTENDANCE_FIELD_LABELS[field]}: "
            f"{_attendance_field_value(field, row, employee)}"
            for field in record_fields
            if _attendance_field_value(field, row, employee) not in (None, "")
        ]
        if details:
            lines.append("- " + "; ".join(details))

    sections = []
    if "count" in fields:
        sections.append(f"Found {len(rows)} attendance record(s).")
    if lines:
        sections.append("Here are the requested attendance details:\n" + "\n".join(lines))
    response = "\n".join(sections)
    if lines and len(rows) > len(lines):
        response += f"\nShowing {len(lines)} of {len(rows)} records."
    return response


def _format_combined_reply(employees, attendance_rows, fields):
    checked_out = sum(
        bool(str(row.get("Check Out") or "").strip())
        for row in attendance_rows or []
    )
    summary_parts = []
    if "employee_count" in fields:
        summary_parts.append(f"{len(employees or [])} active employee(s).")
    if "attendance_count" in fields:
        summary_parts.append(f"{len(attendance_rows or [])} attendance record(s).")
    if "checked_out_count" in fields:
        summary_parts.append(f"{checked_out} record(s) have a check-out.")
    if "open_count" in fields:
        summary_parts.append(
            f"{len(attendance_rows or []) - checked_out} record(s) do not have a check-out."
        )

    record_fields = [
        field for field in fields if field in ATTENDANCE_FIELD_LABELS
    ]
    if attendance_rows and record_fields:
        summary_parts.append(
            _format_attendance_reply(
                attendance_rows,
                employees,
                "attendance_records",
                record_fields,
            )
        )
    elif employees and record_fields:
        summary_parts.append(
            _format_employee_reply(employees, "employee_records", record_fields)
        )

    return "\n".join(summary_parts) or "Which employee or attendance details would you like?"


def generate_supervisor_reply(messages):
    """Route a chat request to the required agents and format their data locally."""
    user_messages = [(role, text) for role, text in messages if role == "user"]
    if not user_messages:
        raise GeminiResponseError("A user message is required to route a chat request.")

    local_plan = _local_data_plan(user_messages[-1][1])
    try:
        plan = generate_data_request_plan(user_messages)
    except (APIError, GeminiConfigurationError, GeminiResponseError) as error:
        if local_plan is None:
            raise
        logger.warning(
            "Gemini routing failed; using local routing for this data query (%s).",
            type(error).__name__,
        )
        plan = local_plan
    else:
        if local_plan is not None:
            plan.update(local_plan)

    sources = set(plan["sources"])

    # General app questions do not need access to employee or attendance records.
    if not sources:
        return generate_chat_reply(user_messages)

    intent = plan["intent"]
    if (
        intent in {"attendance_records", "attendance_summary"}
        and "csv" not in sources
    ):
        raise GeminiResponseError("Gemini did not select the attendance data source.")
    if (
        intent in {"employee_records", "employee_summary"}
        and "database" not in sources
    ):
        raise GeminiResponseError("Gemini did not select the employee data source.")
    if intent == "combined" and not {"csv", "database"}.issubset(sources):
        raise GeminiResponseError("Gemini did not select both required data sources.")

    # Only the selected agents are called; their records stay on this server.
    attendance_rows = None
    employees = None
    if "csv" in sources:
        try:
            attendance_rows = csv_agent.get_csv_data()
        except (OSError, duckdb.Error) as error:
            raise SupervisorDataError(
                "Could not read the attendance CSV data."
            ) from error

    if "database" in sources:
        try:
            employees = database_agent.get_database_data()
        except (ConnectionError, psycopg2.Error) as error:
            raise SupervisorDataError(
                "Could not read employee data from the database."
            ) from error

    if intent in {"employee_records", "employee_summary"}:
        employees = [
            employee
            for employee in employees or []
            if _matches_filters(
                employee,
                "employee_id",
                "employee_name",
                None,
                plan,
            )
        ]
        return _format_employee_reply(employees, intent, plan.get("fields", []))

    if intent in {"attendance_records", "attendance_summary"}:
        attendance_rows = [
            row
            for row in attendance_rows or []
            if _matches_filters(
                row,
                "Employee ID",
                "Employee Name",
                "Date",
                plan,
            )
        ]
        return _format_attendance_reply(
            attendance_rows,
            employees,
            intent,
            plan.get("fields", []),
            plan,
        )

    if intent == "combined":
        employees = [
            employee
            for employee in employees or []
            if _matches_filters(
                employee,
                "employee_id",
                "employee_name",
                None,
                plan,
            )
        ]
        attendance_rows = [
            row
            for row in attendance_rows or []
            if _matches_filters(
                row,
                "Employee ID",
                "Employee Name",
                "Date",
                plan,
            )
        ]
        return _format_combined_reply(
            employees,
            attendance_rows,
            plan.get("fields", []),
        )

    if employees is not None and attendance_rows is not None:
        return _format_combined_reply(
            employees,
            attendance_rows,
            plan.get("fields", []),
        )
    if employees is not None:
        return _format_employee_reply(
            employees,
            "employee_summary",
            plan.get("fields", []),
        )
    return _format_attendance_reply(
        attendance_rows or [],
        employees,
        "attendance_summary",
        plan.get("fields", []),
        plan,
    )