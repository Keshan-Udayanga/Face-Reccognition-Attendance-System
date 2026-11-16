
from src.employee_service import get_registered_employees

employees = get_registered_employees()

print("Total registered face embeddings:", len(employees))

for employee in employees:
    print("----------------------------")
    print("Employee ID:", employee["employee_id"])
    print("Employee Name:", employee["employee_name"])
    print("Embedding dimensions:", len(employee["embedding"]))
