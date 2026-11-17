import unittest
from unittest.mock import patch

from src import employee_service


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, query):
        pass

    def fetchall(self):
        return self.rows

    def close(self):
        pass


class FakeConnection:
    def __init__(self, rows):
        self.fake_cursor = FakeCursor(rows)

    def cursor(self):
        return self.fake_cursor

    def close(self):
        pass


class EmployeeEmbeddingRegistryTests(unittest.TestCase):
    def test_skips_json_null_embeddings_and_keeps_valid_embeddings(self):
        valid_embedding = [0.1] * 512
        connection = FakeConnection([
            (1, "No embedding", None),
            (2, "JSON null", "null"),
            (3, "Valid embedding", valid_embedding),
        ])

        with patch.object(employee_service, "get_connection", return_value=connection):
            employees = employee_service.get_registered_employees()

        self.assertEqual(len(employees), 1)
        self.assertEqual(employees[0]["employee_id"], 3)
        self.assertEqual(employees[0]["embedding"], valid_embedding)


if __name__ == "__main__":
    unittest.main()
