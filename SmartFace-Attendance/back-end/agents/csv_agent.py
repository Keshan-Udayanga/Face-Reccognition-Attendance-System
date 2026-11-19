import duckdb
from pathlib import Path


# Keep the CSV location relative to this agent so it works from any run directory.
ATTENDANCE_DIR = Path(__file__).resolve().parent.parent / "attendance"


def get_connection():
    """Create an in-memory DuckDB connection with attendance CSVs as a view."""
    csv_files = list(ATTENDANCE_DIR.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No attendance CSV files found in {ATTENDANCE_DIR}.")

    # Escape quotes because the directory path is embedded in the DuckDB SQL statement.
    csv_pattern = (ATTENDANCE_DIR / "*.csv").as_posix().replace("'", "''")
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


def get_csv_data():
    """Return attendance rows from all CSV files as dictionaries using DuckDB."""
    connection = get_connection()
    try:
        # DuckDB infers the columns and types, then rows are mapped to their headers.
        result = connection.execute("SELECT * FROM attendance")
        column_names = [column[0] for column in result.description]
        return [
            dict(zip(column_names, row))
            for row in result.fetchall()
        ]
    finally:
        connection.close()