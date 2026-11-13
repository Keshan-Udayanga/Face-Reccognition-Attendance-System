
import cv2

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Camera cannot be opened!")
else:
    print("Camera connected successfully!")

    while True:
        ret, frame = camera.read()

        if not ret:
            print("Cannot read camera frame!")
            break

        cv2.imshow("SmartFace - Camera Test", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

camera.release()
cv2.destroyAllWindows()
