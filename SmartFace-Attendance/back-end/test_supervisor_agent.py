import unittest
from datetime import date, timedelta
from unittest.mock import patch

from google.genai.errors import APIError

from agents import supervisor_agent


class SupervisorAgentTests(unittest.TestCase):
    @patch("agents.supervisor_agent.generate_data_request_plan")
    @patch("agents.supervisor_agent.database_agent.get_database_data")
    @patch("agents.supervisor_agent.csv_agent.get_csv_data")
    def test_routes_attendance_summary_to_csv_only(
        self, get_csv_data, get_database_data, generate_plan
    ):
        generate_plan.return_value = {
            "sources": ["csv"],
            "intent": "attendance_summary",
            "employee_id": "7",
            "employee_name": None,
            "date": "2026-11-19",
            "fields": ["count"],
        }
        get_csv_data.return_value = [
            {
                "Employee ID": 7,
                "Employee Name": "Taylor",
                "Date": date(2026, 11, 19),
                "Check Out": "",
            },
            {
                "Employee ID": 8,
                "Employee Name": "Jordan",
                "Date": date(2026, 11, 19),
                "Check Out": "17:00:00",
            },
        ]

        reply = supervisor_agent.generate_supervisor_reply([("user", "Attendance?")])

        self.assertEqual(
            reply,
            "Found 1 attendance record(s).",
        )
        get_csv_data.assert_called_once_with()
        get_database_data.assert_not_called()

    @patch("agents.supervisor_agent.generate_data_request_plan")
    @patch("agents.supervisor_agent.database_agent.get_database_data")
    @patch("agents.supervisor_agent.csv_agent.get_csv_data")
    def test_fetches_from_both_agents_for_combined_requests(
        self, get_csv_data, get_database_data, generate_plan
    ):
        generate_plan.return_value = {
            "sources": ["csv", "database"],
            "intent": "combined",
            "employee_id": None,
            "employee_name": None,
            "date": None,
            "fields": [
                "employee_count",
                "attendance_count",
                "checked_out_count",
                "employee_name",
                "department",
                "check_in",
                "check_out",
            ],
        }
        get_csv_data.return_value = [
            {
                "Employee ID": 7,
                "Employee Name": "Taylor",
                "Date": date(2026, 11, 19),
                "Check In": "09:00:00",
                "Check Out": "17:00:00",
                "Total Hours": "08:00:00",
            }
        ]
        get_database_data.return_value = [
            {
                "employee_id": 7,
                "employee_name": "Taylor",
                "department": "Engineering",
                "designation": "Developer",
            }
        ]

        reply = supervisor_agent.generate_supervisor_reply([("user", "Show both")])

        self.assertIn(
            "1 active employee(s).\n1 attendance record(s).\n1 record(s) have a check-out.",
            reply,
        )
        self.assertIn("Employee name: Taylor", reply)
        self.assertIn("Department: Engineering", reply)
        self.assertIn("Check-in: 09:00:00", reply)
        self.assertIn("Check-out: 17:00:00", reply)
        self.assertNotIn("Designation", reply)
        self.assertNotIn("Total hours", reply)
        get_csv_data.assert_called_once_with()
        get_database_data.assert_called_once_with()

    @patch("agents.supervisor_agent.generate_data_request_plan")
    @patch("agents.supervisor_agent.generate_chat_reply")
    @patch("agents.supervisor_agent.database_agent.get_database_data")
    @patch("agents.supervisor_agent.csv_agent.get_csv_data")
    def test_general_question_uses_chat_reply_without_data_agents(
        self, get_csv_data, get_database_data, generate_chat_reply, generate_plan
    ):
        generate_plan.return_value = {
            "sources": [],
            "intent": "general",
            "employee_id": None,
            "employee_name": None,
            "date": None,
            "fields": [],
        }
        generate_chat_reply.return_value = "You can use the dashboard to review attendance."

        reply = supervisor_agent.generate_supervisor_reply([("user", "How do I use this app?")])

        self.assertEqual(reply, "You can use the dashboard to review attendance.")
        get_csv_data.assert_not_called()
        get_database_data.assert_not_called()

    @patch("agents.supervisor_agent.generate_data_request_plan")
    @patch("agents.supervisor_agent.database_agent.get_database_data")
    @patch("agents.supervisor_agent.csv_agent.get_csv_data")
    def test_honorific_name_matches_and_only_requested_field_is_returned(
        self, get_csv_data, get_database_data, generate_plan
    ):
        generate_plan.return_value = {
            "sources": ["database"],
            "intent": "employee_records",
            "employee_id": None,
            "employee_name": "Mr.Keshan",
            "date": None,
            "fields": ["employee_name"],
        }
        get_database_data.return_value = [
            {
                "employee_id": 7,
                "employee_name": "Keshan Udayanga",
                "department": "Engineering",
                "designation": "Developer",
            },
            {
                "employee_id": 8,
                "employee_name": "Jordan Taylor",
                "department": "Design",
                "designation": "Designer",
            },
        ]

        reply = supervisor_agent.generate_supervisor_reply(
            [("user", "What is Mr. Keshan's name?")]
        )

        self.assertEqual(reply, "- Employee name: Keshan Udayanga")
        self.assertNotIn("Engineering", reply)
        self.assertNotIn("7", reply)
        get_csv_data.assert_not_called()
        get_database_data.assert_called_once_with()

    @patch("agents.supervisor_agent.generate_data_request_plan")
    @patch("agents.supervisor_agent.database_agent.get_database_data")
    @patch("agents.supervisor_agent.csv_agent.get_csv_data")
    def test_attendance_count_reply_does_not_add_unrequested_details(
        self, get_csv_data, get_database_data, generate_plan
    ):
        generate_plan.return_value = {
            "sources": ["csv"],
            "intent": "attendance_records",
            "employee_id": None,
            "employee_name": None,
            "date": None,
            "fields": ["count"],
        }
        get_csv_data.return_value = [
            {"Employee ID": 7, "Check In": "09:00:00", "Check Out": "17:00:00"},
            {"Employee ID": 8, "Check In": "09:30:00", "Check Out": ""},
        ]

        reply = supervisor_agent.generate_supervisor_reply(
            [("user", "How many attendance records are there?")]
        )

        self.assertEqual(reply, "Found 2 attendance record(s).")
        self.assertNotIn("check-in", reply.casefold())
        get_csv_data.assert_called_once_with()
        get_database_data.assert_not_called()

    @patch("agents.supervisor_agent.generate_data_request_plan")
    @patch("agents.supervisor_agent.database_agent.get_database_data")
    @patch("agents.supervisor_agent.csv_agent.get_csv_data")
    def test_attendance_question_uses_local_router_when_gemini_is_unavailable(
        self, get_csv_data, get_database_data, generate_plan
    ):
        generate_plan.side_effect = APIError(503, {"message": "service unavailable"})
        get_csv_data.return_value = [
            {"Employee ID": 7, "Date": date.today() - timedelta(days=1)},
            {"Employee ID": 8, "Date": date.today()},
        ]

        with self.assertLogs("agents.supervisor_agent", level="WARNING"):
            reply = supervisor_agent.generate_supervisor_reply(
                [("user", "How many employees came yesterday?")]
            )

        self.assertEqual(reply, "Found 1 attendance record(s).")
        get_csv_data.assert_called_once_with()
        get_database_data.assert_not_called()

    @patch("agents.supervisor_agent.generate_data_request_plan")
    @patch("agents.supervisor_agent.database_agent.get_database_data")
    @patch("agents.supervisor_agent.csv_agent.get_csv_data")
    def test_employee_name_and_requested_field_work_when_gemini_is_unavailable(
        self, get_csv_data, get_database_data, generate_plan
    ):
        generate_plan.side_effect = APIError(503, {"message": "service unavailable"})
        get_database_data.return_value = [
            {
                "employee_id": 7,
                "employee_name": "Keshan Udayanga",
                "designation": "Developer",
                "department": "Engineering",
            },
            {
                "employee_id": 8,
                "employee_name": "Jordan Taylor",
                "designation": "Designer",
                "department": "Design",
            },
        ]

        with self.assertLogs("agents.supervisor_agent", level="WARNING"):
            reply = supervisor_agent.generate_supervisor_reply(
                [("user", "What is Mr.Keshan's designation?")]
            )

        self.assertEqual(reply, "- Designation: Developer")
        get_database_data.assert_called_once_with()
        get_csv_data.assert_not_called()

    @patch("agents.supervisor_agent.generate_data_request_plan")
    @patch("agents.supervisor_agent.database_agent.get_database_data")
    @patch("agents.supervisor_agent.csv_agent.get_csv_data")
    def test_attendance_status_question_returns_a_direct_answer(
        self, get_csv_data, get_database_data, generate_plan
    ):
        generate_plan.return_value = {
            "sources": ["csv"],
            "intent": "attendance_records",
            "employee_id": None,
            "employee_name": None,
            "date": None,
            "fields": [],
        }
        get_csv_data.return_value = [
            {
                "Employee ID": 7,
                "Employee Name": "Keshan Udayanga",
                "Date": date.today(),
                "Check In": "09:00:00",
            }
        ]

        reply = supervisor_agent.generate_supervisor_reply(
            [("user", "keshan is attend today ?")]
        )

        self.assertEqual(
            reply,
            f"Yes. Keshan Udayanga has an attendance record for {date.today()}.",
        )
        get_csv_data.assert_called_once_with()
        get_database_data.assert_not_called()

    @patch("agents.supervisor_agent.generate_data_request_plan")
    @patch("agents.supervisor_agent.csv_agent.get_csv_data")
    def test_attendance_status_reports_when_no_record_exists(
        self, get_csv_data, generate_plan
    ):
        generate_plan.return_value = {
            "sources": ["csv"],
            "intent": "attendance_records",
            "employee_id": None,
            "employee_name": None,
            "date": None,
            "fields": [],
        }
        get_csv_data.return_value = []

        reply = supervisor_agent.generate_supervisor_reply(
            [("user", "Is Mr.Keshan attending today?")]
        )

        self.assertEqual(
            reply,
            f"No attendance record found for Keshan on {date.today()}.",
        )


if __name__ == "__main__":
    unittest.main()
