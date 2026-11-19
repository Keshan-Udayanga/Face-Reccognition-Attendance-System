import unittest
from unittest.mock import patch

from agents import database_agent


class DatabaseAgentTests(unittest.TestCase):
    @patch("agents.database_agent.get_all_employees")
    def test_get_database_data_returns_employee_records(self, get_all_employees):
        employee_records = [
            {"employee_id": 7, "employee_name": "Taylor", "department": "Engineering"}
        ]
        get_all_employees.return_value = employee_records

        result = database_agent.get_database_data()

        self.assertEqual(result, employee_records)
        get_all_employees.assert_called_once_with()

    @patch("agents.database_agent.get_all_employees")
    def test_get_database_data_propagates_database_errors(self, get_all_employees):
        get_all_employees.side_effect = ConnectionError("Database connection failed.")

        with self.assertRaisesRegex(ConnectionError, "Database connection failed"):
            database_agent.get_database_data()


if __name__ == "__main__":
    unittest.main()
