
from database.connection import get_connection


def get_all_employees():

    connection = get_connection()

    if connection is None:
        raise ConnectionError("Database connection failed.")

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                employee_id,
                employee_name,
                department,
                is_active,
                contact_number,
                email,
                designation
            FROM employees
            WHERE is_active = TRUE
            ORDER BY employee_name;
        """)

        rows = cursor.fetchall()

        employees = []

        for row in rows:
            employees.append({
                "employee_id": row[0],
                "employee_name": row[1],
                "department": row[2],
                "is_active": row[3],
                "contact_number": row[4],
                "email": row[5],
                "designation": row[6]
            })

        return employees

    finally:
        connection.close()
