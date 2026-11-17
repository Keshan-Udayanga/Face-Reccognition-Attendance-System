
import cv2
import time

from src.face_recognition import generate_face_embedding
from src.employee_service import get_registered_employees
from src.face_matching import find_best_match
from src.attendance_service import mark_attendance


# Load registered employees
registered_employees = get_registered_employees()

print("Registered employees loaded:", len(registered_employees))


# Track employees currently visible
recognized_employees = set()

# Track when employees leave the camera
employee_exit_time = {}

# Track employees seen in the current frame
current_frame_employees = set()


# Load face detector
face_detector = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)


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

    current_frame_employees = set()

    try:

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        detected_faces = face_detector.detectMultiScale(
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

                    employee_id = result["employee_id"]
                    employee_name = result["employee_name"]

                    label = employee_name

                    current_frame_employees.add(employee_id)

                    current_time = time.time()

                    if employee_id not in recognized_employees:

                        previous_exit = employee_exit_time.get(
                            employee_id, 0
                        )

                        if current_time - previous_exit >= 3:

                            attendance_status = mark_attendance(
                                employee_id,
                                employee_name
                            )

                            print(
                                employee_name,
                                "-",
                                attendance_status
                            )

                            label = f"{employee_name} - {attendance_status}"

                        recognized_employees.add(employee_id)

                else:
                    label = "Unknown"

            except Exception as e:

                print("Recognition error:", e)
                label = "Unknown"

            # Draw rectangle
            cv2.rectangle(
                frame,
                (x, y),
                (x+w, y+h),
                (0, 255, 0),
                2
            )

            # Display employee name
            cv2.putText(
                frame,
                label,
                (x, y-10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

        # Detect employees who left the camera
        employees_who_left = recognized_employees - current_frame_employees

        for employee_id in employees_who_left:

            if employee_id not in employee_exit_time:
                employee_exit_time[employee_id] = time.time()

        # Reset tracking after employee has been absent for 3 seconds
        for employee_id in list(recognized_employees):

            if employee_id in current_frame_employees:
                employee_exit_time.pop(employee_id, None)

            elif time.time() - employee_exit_time.get(
                employee_id, time.time()
            ) >= 3:

                recognized_employees.remove(employee_id)
                employee_exit_time.pop(employee_id, None)

    except Exception as e:

        print("Face detection error:", e)

    cv2.imshow("SmartFace - Attendance System", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


camera.release()
cv2.destroyAllWindows()
