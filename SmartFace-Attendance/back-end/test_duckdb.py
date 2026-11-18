
from src.chatbot_employee_service import get_all_employees

employees = get_all_employees()

print("Total Active Employees:", len(employees))

for employee in employees:
    print(employee)
