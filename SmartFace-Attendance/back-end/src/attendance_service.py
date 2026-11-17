
import csv
import os
from datetime import datetime

# Attendance CSV file location
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ATTENDANCE_DIR = os.path.join(BASE_DIR, "attendance")
CSV_FILE = os.path.join(ATTENDANCE_DIR, "attendance.csv")


def create_attendance_file():
    os.makedirs(ATTENDANCE_DIR, exist_ok=True)

    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                "Employee ID",
                "Employee Name",
                "Date",
                "Check In",
                "Check Out"
            ])


def mark_attendance(employee_id, employee_name):
    create_attendance_file()

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")

    rows = []

    with open(CSV_FILE, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    # Find today's attendance record for this employee
    for row in rows:
        if (
            row["Employee ID"] == str(employee_id)
            and row["Date"] == today
        ):
            if row["Check Out"] == "":
                row["Check Out"] = current_time

                with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as file:
                    writer = csv.DictWriter(file, fieldnames=[
                        "Employee ID",
                        "Employee Name",
                        "Date",
                        "Check In",
                        "Check Out"
                    ])
                    writer.writeheader()
                    writer.writerows(rows)

                return "CHECK OUT"

            return "ALREADY COMPLETED"

    # No attendance record exists for today
    rows.append({
        "Employee ID": str(employee_id),
        "Employee Name": employee_name,
        "Date": today,
        "Check In": current_time,
        "Check Out": ""
    })

    with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=[
            "Employee ID",
            "Employee Name",
            "Date",
            "Check In",
            "Check Out"
        ])
        writer.writeheader()
        writer.writerows(rows)

    return "CHECK IN"
