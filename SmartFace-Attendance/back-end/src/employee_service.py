
from database.connection import get_connection
import json


def get_registered_employees():

    connection = get_connection()

    if connection is None:
        raise ConnectionError("Database connection failed.")

    registered_faces = []

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                e.employee_id,
                e.employee_name,
                ef.face_embedding
            FROM employees e
            INNER JOIN employee_faces ef
                ON e.employee_id = ef.employee_id
            WHERE
                e.is_active = TRUE
                AND ef.face_embedding IS NOT NULL
        """)

        rows = cursor.fetchall()

        for row in rows:

            employee_id, employee_name, embedding_data = row

            if isinstance(embedding_data, str):
                embedding = json.loads(embedding_data)
            else:
                embedding = embedding_data

            if embedding is None:
                continue

            if len(embedding) != 512:
                print(f"Invalid embedding for employee {employee_id}")
                continue

            registered_faces.append({
                "employee_id": employee_id,
                "employee_name": employee_name,
                "embedding": embedding
            })

        cursor.close()

        return registered_faces

    finally:
        connection.close()
