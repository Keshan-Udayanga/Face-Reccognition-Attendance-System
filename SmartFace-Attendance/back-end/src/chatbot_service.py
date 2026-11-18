
import duckdb
from pathlib import Path

from src.chatbot_employee_service import get_all_employees


ATTENDANCE_DIR = (
    Path(__file__).resolve().parent.parent / "attendance"
)


def get_connection():

    csv_files = list(ATTENDANCE_DIR.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError("No attendance CSV files found.")

    csv_pattern = (ATTENDANCE_DIR / "*.csv").as_posix()
    csv_pattern = csv_pattern.replace("'", "''")

    connection = duckdb.connect(database=":memory:")

    connection.execute(f"""
        CREATE VIEW attendance AS
        SELECT *
        FROM read_csv_auto(
            '{csv_pattern}',
            union_by_name = true
        )
    """)

    return connection


def get_combined_attendance():

    connection = get_connection()

    try:
        employees = get_all_employees()

        employee_rows = [
            (
                emp["employee_id"],
                emp["employee_name"],
                emp["department"]
            )
            for emp in employees
        ]

        connection.execute("""
            CREATE TABLE employees (
                employee_id INTEGER,
                employee_name VARCHAR,
                department VARCHAR
            )
        """)

        connection.executemany("""
            INSERT INTO employees VALUES (?, ?, ?)
        """, employee_rows)

        result = connection.execute("""
            SELECT
                a."Employee ID" AS employee_id,
                e.employee_name,
                e.department,
                a."Date" AS attendance_date,
                a."Check In" AS check_in,
                a."Check Out" AS check_out,
                a."Total Hours" AS total_hours

            FROM attendance a

            LEFT JOIN employees e
                ON TRY_CAST(a."Employee ID" AS INTEGER)
                = e.employee_id

            ORDER BY a."Date" DESC
        """).df()

        return result

    finally:
        connection.close()
