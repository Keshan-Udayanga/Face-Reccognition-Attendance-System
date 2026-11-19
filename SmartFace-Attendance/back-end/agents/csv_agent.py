import csv
from pathlib import Path


# Keep the CSV location relative to this agent so it works from any run directory.
ATTENDANCE_DIR = Path(__file__).resolve().parent.parent / "attendance"


def get_csv_data():
    """Return attendance rows from every CSV file in the attendance directory."""
    # Sorting makes the combined rows predictable when multiple monthly files exist.
    csv_files = sorted(ATTENDANCE_DIR.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No attendance CSV files found in {ATTENDANCE_DIR}.")

    attendance_rows = []

    for csv_file in csv_files:
        # DictReader uses the CSV header row as keys for each returned row.
        with csv_file.open("r", newline="", encoding="utf-8-sig") as file:
            attendance_rows.extend(csv.DictReader(file))

    return attendance_rows