import csv
import os
import tempfile
import unittest
from datetime import date, timedelta
from unittest.mock import patch

from src import attendance_service


class AttendanceServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.attendance_file = os.path.join(
            self.temporary_directory.name,
            "attendance.csv",
        )
        self.directory_patch = patch.object(
            attendance_service,
            "ATTENDANCE_DIR",
            self.temporary_directory.name,
        )
        self.file_patch = patch.object(
            attendance_service,
            "CSV_FILE",
            self.attendance_file,
        )
        self.directory_patch.start()
        self.file_patch.start()

    def monthly_attendance_file(self, attendance_date):
        return os.path.join(
            self.temporary_directory.name,
            f"attendance_{attendance_date.strftime('%Y-%m')}.csv",
        )

    def tearDown(self):
        self.file_patch.stop()
        self.directory_patch.stop()
        self.temporary_directory.cleanup()

    def test_today_records_include_existing_date_formats(self):
        today = date.today()
        yesterday = today - timedelta(days=1)
        with open(self.attendance_file, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=attendance_service.FIELDNAMES)
            writer.writeheader()
            writer.writerows([
                {
                    "Employee ID": "1",
                    "Employee Name": "Ari",
                    "Date": today.isoformat(),
                    "Check In": "09:00:00",
                    "Check Out": "",
                    "Total Hours": "",
                },
                {
                    "Employee ID": "2",
                    "Employee Name": "Sam",
                    "Date": today.strftime("%m/%d/%Y"),
                    "Check In": "09:10:00",
                    "Check Out": "",
                    "Total Hours": "",
                },
                {
                    "Employee ID": "3",
                    "Employee Name": "Lee",
                    "Date": yesterday.isoformat(),
                    "Check In": "09:15:00",
                    "Check Out": "",
                    "Total Hours": "",
                },
            ])

        records = attendance_service.get_todays_attendance(today)

        self.assertEqual([row["Employee ID"] for row in records], ["1", "2"])

    def test_mark_attendance_checks_in_then_out_without_adding_a_row(self):
        self.assertEqual(
            attendance_service.mark_attendance(7, "Taylor", "Engineering"),
            "CHECK IN",
        )
        self.assertEqual(
            attendance_service.mark_attendance(7, "Taylor", "Engineering"),
            "CHECK OUT",
        )
        self.assertEqual(
            attendance_service.mark_attendance(7, "Taylor", "Engineering"),
            "ALREADY COMPLETED",
        )

        with open(
            self.monthly_attendance_file(date.today()),
            "r",
            newline="",
            encoding="utf-8",
        ) as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Departement"], "Engineering")
        self.assertTrue(rows[0]["Check In"])
        self.assertTrue(rows[0]["Check Out"])

    def test_mark_attendance_reuses_rows_with_legacy_date_format(self):
        today = date.today()
        with open(self.attendance_file, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=attendance_service.FIELDNAMES)
            writer.writeheader()
            writer.writerow({
                "Employee ID": "7",
                "Employee Name": "Taylor",
                "Date": today.strftime("%m/%d/%Y"),
                "Check In": "09:00:00",
                "Check Out": "",
                "Total Hours": "",
            })

        self.assertEqual(attendance_service.mark_attendance(7, "Taylor"), "CHECK OUT")

        with open(
            self.monthly_attendance_file(today),
            "r",
            newline="",
            encoding="utf-8",
        ) as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["Check Out"])

    def test_legacy_attendance_is_split_into_monthly_files(self):
        with open(self.attendance_file, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=attendance_service.FIELDNAMES)
            writer.writeheader()
            writer.writerows([
                {
                    "Employee ID": "1",
                    "Employee Name": "Ari",
                    "Date": "2024-01-31",
                    "Check In": "09:00:00",
                    "Check Out": "17:00:00",
                    "Total Hours": "",
                },
                {
                    "Employee ID": "2",
                    "Employee Name": "Sam",
                    "Date": "02/01/2024",
                    "Check In": "09:15:00",
                    "Check Out": "",
                    "Total Hours": "",
                },
            ])

        self.assertEqual(
            set(attendance_service.get_attendance_months()),
            {"2024-02", "2024-01", date.today().strftime("%Y-%m")},
        )
        for month, expected_id in (("2024-01", "1"), ("2024-02", "2")):
            with open(
                os.path.join(self.temporary_directory.name, f"attendance_{month}.csv"),
                "r",
                newline="",
                encoding="utf-8",
            ) as file:
                self.assertEqual(
                    [row["Employee ID"] for row in csv.DictReader(file)],
                    [expected_id],
                )

    def test_monthly_file_lookup_rejects_invalid_month(self):
        self.assertIsNone(attendance_service.get_monthly_attendance_file("../secret"))
        self.assertIsNone(attendance_service.get_monthly_attendance_file("2024-13"))

    def test_available_months_includes_current_month_without_records(self):
        current_month = date.today().strftime("%Y-%m")

        self.assertIn(current_month, attendance_service.get_attendance_months())
        self.assertTrue(
            os.path.isfile(
                os.path.join(
                    self.temporary_directory.name,
                    f"attendance_{current_month}.csv",
                )
            )
        )


if __name__ == "__main__":
    unittest.main()
