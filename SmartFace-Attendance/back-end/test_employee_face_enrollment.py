import json
import sys
import types
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from src import api


class FakeCursor:
    def __init__(self, existing_face=None):
        self.existing_face = existing_face
        self.executions = []

    def execute(self, query, parameters):
        self.executions.append((query, parameters))

    def fetchone(self):
        return self.existing_face


class EmployeeFaceEnrollmentTests(unittest.TestCase):
    def test_saves_generated_embedding_with_new_profile_photo(self):
        cursor = FakeCursor()
        embedding = [0.1] * 512

        api._save_profile_photo(cursor, 23, b"profile-photo", embedding)

        query, parameters = cursor.executions[-1]
        self.assertIn("INSERT INTO employee_faces", query)
        self.assertEqual(parameters[0], 23)
        self.assertEqual(parameters[1].adapted, b"profile-photo")
        self.assertEqual(json.loads(parameters[2]), embedding)
        self.assertEqual(parameters[3], "Facenet512")

    def test_regenerates_embedding_when_profile_photo_is_replaced(self):
        cursor = FakeCursor(existing_face=(8,))
        embedding = [0.2] * 512

        api._save_profile_photo(cursor, 23, b"new-photo", embedding)

        query, parameters = cursor.executions[0]
        self.assertIn("UPDATE employee_faces", query)
        self.assertIn("face_embedding = %s::jsonb", query)
        self.assertEqual(json.loads(parameters[1]), embedding)
        self.assertEqual(parameters[2], "Facenet512")

    def test_generates_embedding_from_uploaded_photo(self):
        embedding = [0.3] * 512
        face_recognition_module = types.ModuleType("src.face_recognition")
        face_recognition_module.generate_face_embedding = lambda image: embedding

        with patch.dict(sys.modules, {"src.face_recognition": face_recognition_module}):
            self.assertEqual(api._generate_profile_embedding(b"profile-photo"), embedding)

    def test_rejects_profile_photo_without_detectable_face(self):
        face_recognition_module = types.ModuleType("src.face_recognition")

        def fail_embedding(_image):
            raise ValueError("No face detected")

        face_recognition_module.generate_face_embedding = fail_embedding
        with patch.dict(sys.modules, {"src.face_recognition": face_recognition_module}):
            with self.assertRaises(HTTPException) as raised:
                api._generate_profile_embedding(b"profile-photo")

        self.assertEqual(raised.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
