
from src.employee_service import get_registered_employees
from src.face_matching import find_best_match

# Load registered employee embeddings
employees = get_registered_employees()

if not employees:
    print("No registered employees found.")
    exit()

# Use Employee 6's registered embedding as a test input
test_embedding = employees[0]["embedding"]

# Compare with registered employees
result = find_best_match(test_embedding, employees)

if result:
    print("\nFace Matching Result")
    print("----------------------------")
    print("Employee ID:", result["employee_id"])
    print("Employee Name:", result["employee_name"])
    print("Cosine Distance:", result["distance"])
else:
    print("No matching employee found.")
