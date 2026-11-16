
import cv2
import numpy as np
from deepface import DeepFace


def generate_face_embedding(face_image_bytes):
    """
    Convert a database image (BYTEA) into a FaceNet512 embedding.
    """

    # Step 1: Convert database bytes into a NumPy array
    image_array = np.frombuffer(face_image_bytes, dtype=np.uint8)

    # Step 2: Decode bytes into an OpenCV image
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError("Could not decode the employee face image.")

    # Step 3: Generate embedding using FaceNet512
    result = DeepFace.represent(
        img_path=image,
        model_name="Facenet512",
        detector_backend="opencv",
        enforce_detection=True
    )

    # Step 4: Get the 512-dimensional embedding
    embedding = result[0]["embedding"]

    # Step 5: Return embedding as a Python list
    return embedding
