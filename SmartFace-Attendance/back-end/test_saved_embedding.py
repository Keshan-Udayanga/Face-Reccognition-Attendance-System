
import json
from database.connection import get_connection

connection = get_connection()

if connection is None:
    print("Database connection failed.")
    exit()

try:
    cursor = connection.cursor()

    cursor.execute("""
        SELECT employee_id, face_embedding, model_name
        FROM employee_faces
        WHERE face_embedding IS NOT NULL
        ORDER BY face_id
        LIMIT 1
    """)

    row = cursor.fetchone()

    if row is None:
        print("No saved embeddings found.")
    else:
        employee_id, embedding_data, model_name = row

        # PostgreSQL JSONB data
        # may be returned as a Python list or string
        if isinstance(embedding_data, str):
            embedding = json.loads(embedding_data)
        else:
            embedding = embedding_data

        print("Embedding retrieved successfully!")
        print("Employee ID:", employee_id)
        print("Model:", model_name)
        print("Embedding dimensions:", len(embedding))
        print("First 5 values:", embedding[:5])

    cursor.close()

finally:
    connection.close()
