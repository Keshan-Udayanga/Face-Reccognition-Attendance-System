
import cv2

from src.face_recognition import generate_face_embedding
from src.employee_service import get_registered_employees
from src.face_matching import find_best_match


# Load registered employees from PostgreSQL
registered_employees = get_registered_employees()

print("Registered employees loaded:", len(registered_employees))

# Open webcam
camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Cannot open webcam.")
    exit()

print("Camera started. Press Q to quit.")

while True:

    success, frame = camera.read()

    if not success:
        print("Cannot read camera frame.")
        break

    # Detect faces in the current frame
    try:
        faces = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        detected_faces = faces.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80)
        )

        for (x, y, w, h) in detected_faces:

            face_image = frame[y:y+h, x:x+w]

            try:
                embedding = generate_face_embedding(
                    cv2.imencode(".jpg", face_image)[1].tobytes()
                )

                result = find_best_match(
                    embedding,
                    registered_employees
                )

                if result:
                    label = result["employee_name"]
                else:
                    label = "Unknown"

            except Exception as e:
                print("Recognition error:", e)
                label = "Unknown"

            # Draw rectangle and employee name
            cv2.rectangle(
                frame,
                (x, y),
                (x+w, y+h),
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                label,
                (x, y-10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

    except Exception as e:
        print("Face detection error:", e)

    cv2.imshow("SmartFace - Live Recognition", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()

