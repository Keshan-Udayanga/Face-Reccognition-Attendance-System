import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

def get_connection():
    try:
        # Retrieve database connection parameters from environment variables
        db_host = os.getenv("DB_HOST")
        db_port = os.getenv("DB_PORT")
        db_name = os.getenv("DB_NAME")
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")

        # Establish a connection to the PostgreSQL database
        connection = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )

        print("Database connection established successfully.")
        return connection

    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None