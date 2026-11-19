import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from agents import csv_agent


class CsvAgentTests(unittest.TestCase):
    def test_get_csv_data_combines_rows_from_all_attendance_files(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            attendance_directory = Path(temporary_directory)

            # Each file represents one month and shares the same attendance columns.
            for filename, employee_id in (
                ("attendance_2026-01.csv", "12"),
                ("attendance_2026-02.csv", "34"),
            ):
                with (attendance_directory / filename).open(
                    "w", newline="", encoding="utf-8"
                ) as file:
                    writer = csv.DictWriter(file, fieldnames=["Employee ID", "Date"])
                    writer.writeheader()
                    writer.writerow({"Employee ID": employee_id, "Date": "2026-01-01"})

            with patch.object(csv_agent, "ATTENDANCE_DIR", attendance_directory):
                rows = csv_agent.get_csv_data()

        self.assertEqual(
            rows,
            [
                {"Employee ID": 12, "Date": date(2026, 1, 1)},
                {"Employee ID": 34, "Date": date(2026, 1, 1)},
            ],
        )

    def test_get_csv_data_reports_when_no_csv_files_exist(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch.object(
                csv_agent, "ATTENDANCE_DIR", Path(temporary_directory)
            ):
                with self.assertRaises(FileNotFoundError):
                    csv_agent.get_csv_data()


if __name__ == "__main__":
    unittest.main()
