from src.chatbot_employee_service import get_all_employees


def get_database_data():
    """Return active employee records from the PostgreSQL database."""
    # Reuse the existing service so database querying and connection cleanup stay centralized.
    return get_all_employees()