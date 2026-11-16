
import json

from database.connection import get_connection
from src.face_recognition import generate_face_embedding

connection = get_connection()

if connection is None:
    print("Database connection failed.")
    exit()

try:
    cursor = connection.cursor()

    cursor.execute("""
        SELECT face_id, employee_id, face_image
        FROM employee_faces
        ORDER BY face_id
        LIMIT 1
    """)

    row = cursor.fetchone()

    if row is None:
        print("No employee face image found.")
    else:
        face_id, employee_id, face_image_bytes = row

        print(f"Processing employee ID: {employee_id}")

        # Generate FaceNet512 embedding
        embedding = generate_face_embedding(face_image_bytes)

        print("Embedding generated successfully!")
        print("Embedding dimensions:", len(embedding))

        # Convert embedding into JSON format
        embedding_json = json.dumps(embedding)

        # Save embedding into PostgreSQL
        cursor.execute("""
            UPDATE employee_faces
            SET face_embedding = %s::jsonb,
                model_name = %s
            WHERE face_id = %s
        """, (embedding_json, "Facenet512", face_id))

        connection.commit()

        print("Face embedding saved successfully!")

    cursor.close()

except Exception as e:
    connection.rollback()
    print("Error:", e)

finally:
    connection.close()
