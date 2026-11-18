
import csv
import os
import re
import threading
from datetime import date, datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ATTENDANCE_DIR = os.path.join(BASE_DIR, "attendance")

CSV_FILE = os.path.join(ATTENDANCE_DIR, "attendance.csv")

FIELDNAMES = [
    "Employee ID",
    "Employee Name",
    "Departement",
    "Date",
    "Check In",
    "Check Out",
    "Total Hours"
]

_ATTENDANCE_LOCK = threading.Lock()


def calculate_working_hours(check_in, check_out):

    start_time = datetime.strptime(check_in, "%H:%M:%S")
    end_time = datetime.strptime(check_out, "%H:%M:%S")

    duration = end_time - start_time

    total_seconds = int(duration.total_seconds())

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _monthly_csv_file(month):
    return os.path.join(ATTENDANCE_DIR, f"attendance_{month}.csv")


def _parse_attendance_date(value):
    for date_format in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, date_format).date()
        except (TypeError, ValueError):
            continue
    return None


def _write_attendance_file(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def _migrate_legacy_attendance():
    if not os.path.exists(CSV_FILE):
        return

    grouped_rows = {}
    with open(CSV_FILE, "r", newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            row_date = _parse_attendance_date(row.get("Date"))
            if row_date is None:
                continue

            monthly_row = {field: row.get(field, "") or "" for field in FIELDNAMES}
            if (
                not monthly_row["Total Hours"]
                and monthly_row["Check In"]
                and monthly_row["Check Out"]
            ):
                monthly_row["Total Hours"] = calculate_working_hours(
                    monthly_row["Check In"],
                    monthly_row["Check Out"],
                )
            grouped_rows.setdefault(row_date.strftime("%Y-%m"), []).append(monthly_row)

    for month, rows in grouped_rows.items():
        path = _monthly_csv_file(month)
        if not os.path.exists(path):
            _write_attendance_file(path, rows)


def create_attendance_file(today=None):
    os.makedirs(ATTENDANCE_DIR, exist_ok=True)
    if today is None:
        today = datetime.now().date()

    _migrate_legacy_attendance()
    path = _monthly_csv_file(today.strftime("%Y-%m"))
    if not os.path.exists(path):
        _write_attendance_file(path, [])
    return path


def mark_attendance(employee_id, employee_name, department=""):
    with _ATTENDANCE_LOCK:
        now = datetime.now()
        csv_file = create_attendance_file(now.date())

        today = now.strftime("%Y-%m-%d")
        today_formats = {today, now.strftime("%m/%d/%Y")}
        current_time = now.strftime("%H:%M:%S")

        with open(csv_file, "r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            rows = list(reader)

        for row in rows:

            if (
                row["Employee ID"] == str(employee_id)
                and row["Date"] in today_formats
            ):

                if row["Check Out"] == "":

                    row["Check Out"] = current_time

                    row["Total Hours"] = calculate_working_hours(
                        row["Check In"],
                        current_time
                    )

                    _write_attendance_file(csv_file, rows)

                    return "CHECK OUT"

                return "ALREADY COMPLETED"

        rows.append({
            "Employee ID": str(employee_id),
            "Employee Name": employee_name,
            "Departement": department,
            "Date": today,
            "Check In": current_time,
            "Check Out": "",
            "Total Hours": ""
        })

        _write_attendance_file(csv_file, rows)

        return "CHECK IN"


def get_todays_attendance(today=None):
    with _ATTENDANCE_LOCK:
        if today is None:
            today = datetime.now().date()
        elif isinstance(today, datetime):
            today = today.date()
        elif not isinstance(today, date):
            raise TypeError("today must be a date or datetime.")

        csv_file = create_attendance_file(today)
        accepted_dates = {
            today.strftime("%Y-%m-%d"),
            today.strftime("%m/%d/%Y"),
        }

        with open(csv_file, "r", newline="", encoding="utf-8") as file:
            return [
                row
                for row in csv.DictReader(file)
                if row.get("Date") in accepted_dates
            ]


def get_attendance_months():
    with _ATTENDANCE_LOCK:
        create_attendance_file()

        months = set()
        for filename in os.listdir(ATTENDANCE_DIR):
            match = re.fullmatch(r"attendance_(\d{4}-\d{2})\.csv", filename)
            if match:
                try:
                    datetime.strptime(match.group(1), "%Y-%m")
                except ValueError:
                    continue
                months.add(match.group(1))
        return sorted(months, reverse=True)


def get_monthly_attendance_file(month):
    if not isinstance(month, str) or not re.fullmatch(r"\d{4}-\d{2}", month):
        return None
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError:
        return None

    with _ATTENDANCE_LOCK:
        os.makedirs(ATTENDANCE_DIR, exist_ok=True)
        _migrate_legacy_attendance()
        path = _monthly_csv_file(month)
        return path if os.path.isfile(path) else None
