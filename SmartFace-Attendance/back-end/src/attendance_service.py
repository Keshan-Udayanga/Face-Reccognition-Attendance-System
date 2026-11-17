
import csv
import os
import threading
from datetime import date, datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ATTENDANCE_DIR = os.path.join(BASE_DIR, "attendance")

CSV_FILE = os.path.join(ATTENDANCE_DIR, "attendance.csv")

FIELDNAMES = [
    "Employee ID",
    "Employee Name",
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


def create_attendance_file():

    os.makedirs(ATTENDANCE_DIR, exist_ok=True)

    if not os.path.exists(CSV_FILE):

        with open(CSV_FILE, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
            writer.writeheader()

        return

    # Upgrade existing CSV files if Total Hours column is missing
    with open(CSV_FILE, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        existing_fields = reader.fieldnames or []

    if "Total Hours" not in existing_fields:

        for row in rows:

            row["Total Hours"] = ""

            if row.get("Check In") and row.get("Check Out"):
                row["Total Hours"] = calculate_working_hours(
                    row["Check In"],
                    row["Check Out"]
                )

        with open(CSV_FILE, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)


def mark_attendance(employee_id, employee_name):

    with _ATTENDANCE_LOCK:
        create_attendance_file()

        now = datetime.now()

        today = now.strftime("%Y-%m-%d")
        today_formats = {today, now.strftime("%m/%d/%Y")}
        current_time = now.strftime("%H:%M:%S")

        with open(CSV_FILE, "r", newline="", encoding="utf-8") as file:
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

                    with open(CSV_FILE, "w", newline="", encoding="utf-8") as file:
                        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
                        writer.writeheader()
                        writer.writerows(rows)

                    return "CHECK OUT"

                return "ALREADY COMPLETED"

        rows.append({
            "Employee ID": str(employee_id),
            "Employee Name": employee_name,
            "Date": today,
            "Check In": current_time,
            "Check Out": "",
            "Total Hours": ""
        })

        with open(CSV_FILE, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

        return "CHECK IN"


def get_todays_attendance(today=None):
    with _ATTENDANCE_LOCK:
        create_attendance_file()

        if today is None:
            today = datetime.now().date()
        elif isinstance(today, datetime):
            today = today.date()
        elif not isinstance(today, date):
            raise TypeError("today must be a date or datetime.")

        accepted_dates = {
            today.strftime("%Y-%m-%d"),
            today.strftime("%m/%d/%Y"),
        }

        with open(CSV_FILE, "r", newline="", encoding="utf-8") as file:
            return [
                row
                for row in csv.DictReader(file)
                if row.get("Date") in accepted_dates
            ]
