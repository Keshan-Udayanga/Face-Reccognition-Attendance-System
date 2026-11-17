
import numpy as np


def cosine_distance(embedding1, embedding2):

    vector1 = np.array(embedding1, dtype=np.float32)
    vector2 = np.array(embedding2, dtype=np.float32)

    norm1 = np.linalg.norm(vector1)
    norm2 = np.linalg.norm(vector2)

    if norm1 == 0 or norm2 == 0:
        raise ValueError("Invalid zero-length embedding.")

    similarity = np.dot(vector1, vector2) / (norm1 * norm2)

    distance = 1 - similarity

    return float(distance)


def find_best_match(input_embedding, registered_faces):

    best_match = None
    lowest_distance = float("inf")

    for employee in registered_faces:

        distance = cosine_distance(
            input_embedding,
            employee["embedding"]
        )

        if distance < lowest_distance:

            lowest_distance = distance
            best_match = employee

    # No registered employees
    if best_match is None:
        return None

    # Temporary threshold for initial testing only
    threshold = 0.40

    # Reject unknown faces
    if lowest_distance > threshold:
        return None

    return {
        "employee_id": best_match["employee_id"],
        "employee_name": best_match["employee_name"],
        "distance": lowest_distance
    }
