from datetime import date, datetime

import duckdb
import psycopg2

from agents import csv_agent, database_agent
from src.gemini_chat_service import (
    GeminiResponseError,
    generate_chat_reply,
    generate_data_request_plan,
)


class SupervisorDataError(Exception):
    """Raised when a selected data agent cannot retrieve its records."""


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


def _matches_filters(row, employee_id_key, employee_name_key, date_key, plan):
    requested_id = plan.get("employee_id")
    if requested_id and str(row.get(employee_id_key, "")).strip() != requested_id:
        return False

    requested_name = plan.get("employee_name")
    if requested_name:
        row_name = str(row.get(employee_name_key, "")).casefold()
        if requested_name.casefold() not in row_name:
            return False

    requested_date = plan.get("date")
    if (
        requested_date
        and date_key
        and _normalise_date(row.get(date_key, "")) != requested_date
    ):
        return False

    return True


def _format_employee_reply(employees, intent):
    if intent == "employee_summary":
        return f"There are {len(employees)} active employees in the database."

    if not employees:
        return "I couldn't find any active employees matching your request."

    lines = []
    for employee in employees[:10]:
        department = employee.get("department") or "Department not listed"
        designation = employee.get("designation") or "Role not listed"
        lines.append(
            f"- {employee.get('employee_name', 'Name not listed')} "
            f"(ID: {employee.get('employee_id')}, {department}, {designation})"
        )

    response = "Here are the matching active employees:\n" + "\n".join(lines)
    if len(employees) > len(lines):
        response += f"\nShowing {len(lines)} of {len(employees)} employees."
    return response


def _format_attendance_reply(rows, employees, intent):
    if not rows:
        return "I couldn't find attendance records matching your request."

    completed = sum(bool(str(row.get("Check Out") or "").strip()) for row in rows)
    if intent == "attendance_summary":
        open_records = len(rows) - completed
        return (
            f"Found {len(rows)} attendance record(s). "
            f"{completed} have a check-out recorded, and {open_records} do not."
        )

    employee_by_id = {
        str(employee.get("employee_id")): employee
        for employee in employees or []
    }
    lines = []
    for row in rows[:10]:
        employee_id = str(row.get("Employee ID", ""))
        employee = employee_by_id.get(employee_id, {})
        name = (
            employee.get("employee_name")
            or row.get("Employee Name")
            or "Name not listed"
        )
        department = employee.get("department") or row.get("Departement")
        check_out = row.get("Check Out") or "Not recorded"
        details = (
            f"- {name} (ID: {employee_id}) - {row.get('Date', 'Date not listed')}; "
            f"check-in: {row.get('Check In') or 'Not recorded'}; "
            f"check-out: {check_out}; "
            f"total hours: {row.get('Total Hours') or 'Not recorded'}"
        )
        if department:
            details += f"; department: {department}"
        lines.append(details)

    response = "Here are the matching attendance records:\n" + "\n".join(lines)
    if len(rows) > len(lines):
        response += f"\nShowing {len(lines)} of {len(rows)} records."
    return response


def _format_combined_reply(employees, attendance_rows):
    employee_count = len(employees or [])
    attendance_count = len(attendance_rows or [])
    checked_out = sum(
        bool(str(row.get("Check Out") or "").strip())
        for row in attendance_rows or []
    )
    response = (
        f"I found {employee_count} active employee record(s) and "
        f"{attendance_count} attendance record(s). "
        f"{checked_out} attendance record(s) include a check-out."
    )
    if employees:
        response += "\n\n" + _format_employee_reply(employees, "employee_records")
    if attendance_rows:
        response += "\n\n" + _format_attendance_reply(
            attendance_rows,
            employees,
            "attendance_records",
        )
    return response


def generate_supervisor_reply(messages):
    """Route a chat request to the required agents and format their data locally."""
    user_messages = [(role, text) for role, text in messages if role == "user"]
    if not user_messages:
        raise GeminiResponseError("A user message is required to route a chat request.")

    plan = generate_data_request_plan(user_messages)
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
        return _format_employee_reply(employees, intent)

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
        return _format_attendance_reply(attendance_rows, employees, intent)

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
        return _format_combined_reply(employees, attendance_rows)

    if employees is not None and attendance_rows is not None:
        return _format_combined_reply(employees, attendance_rows)
    if employees is not None:
        return _format_employee_reply(employees, "employee_summary")
    return _format_attendance_reply(
        attendance_rows or [],
        employees,
        "attendance_summary",
    )