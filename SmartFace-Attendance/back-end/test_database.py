
from database.connection import get_connection

connection = get_connection()

if connection:
    print("SmartFace database is ready!")

    connection.close()
    print("Database connection closed.")
else:
    print("Please check your database settings.")
