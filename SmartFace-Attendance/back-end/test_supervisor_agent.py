import unittest
from datetime import date
from unittest.mock import patch

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
            "Found 1 attendance record(s). 0 have a check-out recorded, and 1 do not.",
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
            "I found 1 active employee record(s) and 1 attendance record(s). "
            "1 attendance record(s) include a check-out.",
            reply,
        )
        self.assertIn("Taylor (ID: 7, Engineering, Developer)", reply)
        self.assertIn("Taylor (ID: 7)", reply)
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
        }
        generate_chat_reply.return_value = "You can use the dashboard to review attendance."

        reply = supervisor_agent.generate_supervisor_reply([("user", "How do I use this app?")])

        self.assertEqual(reply, "You can use the dashboard to review attendance.")
        get_csv_data.assert_not_called()
        get_database_data.assert_not_called()


if __name__ == "__main__":
    unittest.main()
