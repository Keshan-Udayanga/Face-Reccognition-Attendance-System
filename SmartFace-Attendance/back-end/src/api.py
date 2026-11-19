import json
import os
import re
import threading
import time
import uuid
from datetime import datetime
from typing import Literal, Optional

import cv2
import numpy as np
import psycopg2
from google.genai.errors import APIError
from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from agents.supervisor_agent import SupervisorDataError, generate_supervisor_reply
from database.connection import get_connection
from src.attendance_service import (
    get_attendance_months,
    get_monthly_attendance_file,
    get_todays_attendance,
    mark_attendance,
)
from src.employee_service import get_registered_employees
from src.face_matching import find_best_match
from src.gemini_chat_service import (
    GeminiConfigurationError,
    GeminiResponseError,
)

app = FastAPI(title="SmartFace Employee API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1234",
        "http://127.0.0.1:1234",
    ],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)

MAX_IMAGE_SIZE_BYTES = 1024 * 1024
MAX_FRAME_SIZE_BYTES = 4 * 1024 * 1024
FACE_EMBEDDING_MODEL = "Facenet512"
RECOGNITION_REARM_SECONDS = 3
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
}
ALLOWED_FRAME_TYPES = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
}
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_PATTERN = re.compile(r"^\+?[\d\s().-]+$")
_FACE_DETECTOR = None
_RECOGNITION_LOCK = threading.RLock()
_RECOGNITION_SESSIONS = {}


class ChatMessage(BaseModel):
    role: Literal["user", "model"]
    text: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)


def _connect():
    connection = get_connection()
    if connection is None:
        raise HTTPException(
            status_code=503,
            detail="Could not connect to PostgreSQL. Check the backend database settings.",
        )
    return connection


@app.post("/api/chat")
def chat(request: ChatRequest):
    try:
        reply = generate_supervisor_reply(
            [(message.role, message.text) for message in request.messages]
        )
    except GeminiConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except GeminiResponseError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except SupervisorDataError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except APIError as error:
        raise HTTPException(
            status_code=502,
            detail="Gemini AI could not complete the request. Check the model, API key, and quota.",
        ) from error

    return {"reply": reply}


def _employee_response(row, api_origin):
    employee_id = row[0]
    has_photo = bool(row[9])
    return {
        "id": str(employee_id),
        "employeeId": str(employee_id),
        "fullName": row[1],
        "department": row[2] or "",
        "email": row[3] or "",
        "contactNumber": row[4] or "",
        "designation": row[5] or "",
        "address": row[6] or "",
        "status": "Active" if row[7] is not False else "Inactive",
        "attendanceStatus": None,
        "createdAt": row[8].isoformat() if row[8] else None,
        "photoUrl": (
            f"{api_origin}/api/employees/{employee_id}/photo"
            f"?v={row[10].timestamp() if row[10] else 0}"
            if has_photo
            else None
        ),
    }


def _employee_select():
    return """
        SELECT e.employee_id, e.employee_name, e.department, e.email,
               e.contact_number, e.designation, e.address, e.is_active,
               e.created_at, face.face_id IS NOT NULL, face.created_at
        FROM employees AS e
        LEFT JOIN LATERAL (
            SELECT face_id, created_at
            FROM employee_faces
            WHERE employee_id = e.employee_id
            ORDER BY created_at DESC NULLS LAST, face_id DESC
            LIMIT 1
        ) AS face ON TRUE
    """


def _validate_employee(employee_name, department, email, contact_number):
    if not employee_name.strip():
        raise HTTPException(status_code=422, detail="Full name is required.")
    if not department.strip():
        raise HTTPException(status_code=422, detail="Department is required.")
    if not EMAIL_PATTERN.fullmatch(email.strip()):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    digit_count = len(re.sub(r"\D", "", contact_number))
    if (
        not PHONE_PATTERN.fullmatch(contact_number.strip())
        or digit_count < 7
        or digit_count > 15
    ):
        raise HTTPException(
            status_code=422,
            detail="Enter a valid contact number containing 7 to 15 digits.",
        )


async def _read_profile_photo(photo: Optional[UploadFile]):
    if photo is None:
        return None

    image_prefixes = ALLOWED_IMAGE_TYPES.get(photo.content_type or "")
    if image_prefixes is None:
        raise HTTPException(
            status_code=422,
            detail="Profile photo must be a JPG, JPEG, or PNG image.",
        )

    image_bytes = await photo.read(MAX_IMAGE_SIZE_BYTES + 1)
    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Profile photo must be no larger than 1 MB.",
        )
    if not image_bytes or not image_bytes.startswith(image_prefixes):
        raise HTTPException(
            status_code=422,
            detail="The uploaded file is not a valid JPG or PNG image.",
        )

    return image_bytes


def _generate_profile_embedding(image_bytes):
    try:
        from src.face_recognition import generate_face_embedding
    except (ImportError, ValueError) as error:
        raise HTTPException(
            status_code=503,
            detail="Face recognition dependencies could not be loaded.",
        ) from error

    try:
        embedding = generate_face_embedding(image_bytes)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail="The profile photo must contain a clearly visible face.",
        ) from error

    if len(embedding) != 512:
        raise HTTPException(
            status_code=422,
            detail="Could not create a valid face embedding from the profile photo.",
        )
    return embedding


def _save_profile_photo(cursor, employee_id, image_bytes, embedding):
    if image_bytes is None:
        return

    embedding_json = json.dumps(embedding)
    cursor.execute(
        """
        UPDATE employee_faces
        SET face_image = %s,
            face_embedding = %s::jsonb,
            model_name = %s,
            created_at = CURRENT_TIMESTAMP
        WHERE face_id = (
            SELECT face_id
            FROM employee_faces
            WHERE employee_id = %s
            ORDER BY created_at DESC NULLS LAST, face_id DESC
            LIMIT 1
        )
        RETURNING face_id
        """,
        (
            psycopg2.Binary(image_bytes),
            embedding_json,
            FACE_EMBEDDING_MODEL,
            employee_id,
        ),
    )
    if cursor.fetchone() is None:
        cursor.execute(
            """
            INSERT INTO employee_faces (employee_id, face_image, face_embedding, model_name)
            VALUES (%s, %s, %s::jsonb, %s)
            """,
            (
                employee_id,
                psycopg2.Binary(image_bytes),
                embedding_json,
                FACE_EMBEDDING_MODEL,
            ),
        )


def _fetch_employee(cursor, employee_id, api_origin):
    cursor.execute(
        _employee_select() + " WHERE e.employee_id = %s",
        (employee_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Employee not found.")
    return _employee_response(row, api_origin)


@app.get("/api/health")
def health_check():
    connection = _connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return {"status": "ok"}
    finally:
        connection.close()


@app.post("/api/attendance/recognition/start", status_code=201)
def start_recognition():
    try:
        registered_employees = get_registered_employees()
    except ConnectionError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    session_id = uuid.uuid4().hex
    now = time.monotonic()
    with _RECOGNITION_LOCK:
        expired_sessions = [
            existing_id
            for existing_id, session in _RECOGNITION_SESSIONS.items()
            if now - session["last_activity"] > 1800
        ]
        for existing_id in expired_sessions:
            del _RECOGNITION_SESSIONS[existing_id]

        _RECOGNITION_SESSIONS[session_id] = {
            "employees": registered_employees,
            "employee_details": {},
            "last_seen": {},
            "absent_since": {},
            "last_activity": now,
        }

    return {
        "sessionId": session_id,
        "status": "ready",
        "registeredEmployees": len(registered_employees),
    }


@app.delete("/api/attendance/recognition/{session_id}", status_code=204)
def stop_recognition(session_id: str):
    with _RECOGNITION_LOCK:
        _RECOGNITION_SESSIONS.pop(session_id, None)
    return Response(status_code=204)


@app.post("/api/attendance/recognition/frame")
def recognize_frame(
    request: Request,
    session_id: str = Form(...),
    frame: UploadFile = File(...),
):
    global _FACE_DETECTOR

    if frame.content_type not in ALLOWED_FRAME_TYPES:
        raise HTTPException(
            status_code=422,
            detail="Camera frame must be a JPG or PNG image.",
        )

    frame_bytes = frame.file.read(MAX_FRAME_SIZE_BYTES + 1)
    if len(frame_bytes) > MAX_FRAME_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Camera frame is too large.")
    if (
        not frame_bytes
        or not frame_bytes.startswith(ALLOWED_FRAME_TYPES[frame.content_type])
    ):
        raise HTTPException(status_code=422, detail="Invalid camera frame image.")

    with _RECOGNITION_LOCK:
        session = _RECOGNITION_SESSIONS.get(session_id)
        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Recognition session is not active. Start recognition again.",
            )
        session["last_activity"] = time.monotonic()
        employees = session["employees"]

    if _FACE_DETECTOR is None:
        detector_path = os.path.join(
            cv2.data.haarcascades,
            "haarcascade_frontalface_default.xml",
        )
        if not os.path.isfile(detector_path):
            raise HTTPException(
                status_code=503,
                detail="The OpenCV face detection cascade is not installed.",
            )
        _FACE_DETECTOR = cv2.CascadeClassifier(detector_path)

    if _FACE_DETECTOR.empty():
        raise HTTPException(status_code=503, detail="The face detector is unavailable.")

    image = cv2.imdecode(np.frombuffer(frame_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=422, detail="Could not decode camera frame.")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    detected_faces = _FACE_DETECTOR.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80),
    )
    faces = []
    present_employee_ids = set()

    try:
        from src.face_recognition import generate_face_embedding
    except (ImportError, ValueError) as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "Face recognition dependencies could not be loaded. "
                "Check the TensorFlow and DeepFace installation."
            ),
        ) from error

    for (x, y, width, height) in detected_faces:
        face_image = image[y:y + height, x:x + width]
        encoded, encoded_face = cv2.imencode(".jpg", face_image)
        if not encoded:
            raise HTTPException(status_code=422, detail="Could not process detected face.")

        embedding = generate_face_embedding(encoded_face.tobytes())
        match = find_best_match(embedding, employees)
        if match is None:
            faces.append({
                "recognized": False,
                "status": "Unknown Person",
                "employee": None,
                "attendanceAction": None,
                "timestamp": None,
                "newAttendance": False,
                "isNewRecognition": False,
            })
            continue

        employee_id = match["employee_id"]
        present_employee_ids.add(employee_id)
        now = time.monotonic()
        with _RECOGNITION_LOCK:
            session = _RECOGNITION_SESSIONS.get(session_id)
            if session is None:
                raise HTTPException(
                    status_code=404,
                    detail="Recognition session is no longer active.",
                )

            last_seen = session["last_seen"]
            absent_since = session["absent_since"]
            employee_absent_since = absent_since.get(employee_id)
            if (
                employee_absent_since is not None
                and now - employee_absent_since >= RECOGNITION_REARM_SECONDS
            ):
                del last_seen[employee_id]
                del absent_since[employee_id]

            is_new_recognition = employee_id not in last_seen
            last_seen[employee_id] = now
            absent_since.pop(employee_id, None)
            session["last_activity"] = now

            employee = session["employee_details"].get(employee_id)
            if employee is None:
                connection = _connect()
                try:
                    with connection.cursor() as cursor:
                        employee = _fetch_employee(
                            cursor,
                            employee_id,
                            str(request.base_url).rstrip("/"),
                        )
                finally:
                    connection.close()
                session["employee_details"][employee_id] = employee

            attendance_action = None
            timestamp = None
            if is_new_recognition:
                attendance_action = mark_attendance(
                    employee_id,
                    employee["fullName"],
                    employee.get("department", "") or "",
                )
                if attendance_action in ("CHECK IN", "CHECK OUT"):
                    timestamp = datetime.now().isoformat(timespec="seconds")

            faces.append({
                "recognized": True,
                "status": "Recognized",
                "employee": employee,
                "attendanceAction": attendance_action,
                "timestamp": timestamp,
                "newAttendance": attendance_action in ("CHECK IN", "CHECK OUT"),
                "isNewRecognition": is_new_recognition,
            })

    with _RECOGNITION_LOCK:
        session = _RECOGNITION_SESSIONS.get(session_id)
        if session is not None:
            now = time.monotonic()
            session["last_activity"] = now
            last_seen = session["last_seen"]
            absent_since = session["absent_since"]
            for employee_id in list(last_seen):
                if employee_id in present_employee_ids:
                    absent_since.pop(employee_id, None)
                    continue
                absent_since.setdefault(employee_id, now)
                if now - absent_since[employee_id] >= RECOGNITION_REARM_SECONDS:
                    del last_seen[employee_id]
                    del absent_since[employee_id]

    return {"faces": faces}


@app.get("/api/attendance/today")
def today_attendance():
    rows = get_todays_attendance()
    return [
        {
            "employeeId": row["Employee ID"],
            "employeeName": row["Employee Name"],
            "checkIn": row.get("Check In", ""),
            "checkOut": row.get("Check Out", ""),
            "totalHours": row.get("Total Hours", ""),
            "status": "Checked out" if row.get("Check Out") else "Present",
        }
        for row in rows
    ]


@app.get("/api/attendance/months")
def attendance_months():
    return get_attendance_months()


@app.get("/api/attendance/monthly/{month}")
def download_monthly_attendance(month: str):
    csv_file = get_monthly_attendance_file(month)
    if csv_file is None:
        raise HTTPException(status_code=404, detail="Attendance CSV for this month was not found.")
    return FileResponse(
        csv_file,
        media_type="text/csv",
        filename=os.path.basename(csv_file),
    )


@app.get("/api/employees")
def list_employees(request: Request):
    connection = _connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(_employee_select() + " ORDER BY e.employee_name")
            api_origin = str(request.base_url).rstrip("/")
            return [_employee_response(row, api_origin) for row in cursor.fetchall()]
    finally:
        connection.close()


@app.get("/api/employees/{employee_id}")
def get_employee(employee_id: int, request: Request):
    connection = _connect()
    try:
        with connection.cursor() as cursor:
            return _fetch_employee(cursor, employee_id, str(request.base_url).rstrip("/"))
    finally:
        connection.close()


@app.get("/api/employees/{employee_id}/photo")
def get_employee_photo(employee_id: int):
    connection = _connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT face_image
                FROM employee_faces
                WHERE employee_id = %s
                ORDER BY created_at DESC NULLS LAST, face_id DESC
                LIMIT 1
                """,
                (employee_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Profile photo not found.")
            image_bytes = bytes(row[0])
    finally:
        connection.close()

    content_type = "image/png" if image_bytes.startswith(b"\x89PNG\r\n\x1a\n") else "image/jpeg"
    return Response(
        content=image_bytes,
        media_type=content_type,
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/employees", status_code=201)
async def create_employee(
    request: Request,
    employee_name: str = Form(...),
    department: str = Form(...),
    email: str = Form(...),
    contact_number: str = Form(...),
    designation: str = Form(""),
    address: str = Form(""),
    photo: Optional[UploadFile] = File(None),
):
    _validate_employee(employee_name, department, email, contact_number)
    image_bytes = await _read_profile_photo(photo)
    embedding = _generate_profile_embedding(image_bytes) if image_bytes else None
    connection = _connect()
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO employees (
                        employee_name, department, email,
                        contact_number, designation, address, is_active
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                    RETURNING employee_id
                    """,
                    (
                        employee_name.strip(),
                        department.strip(),
                        email.strip(),
                        contact_number.strip(),
                        designation.strip(),
                        address.strip(),
                    ),
                )
                employee_id = cursor.fetchone()[0]
                _save_profile_photo(cursor, employee_id, image_bytes, embedding)
                employee = _fetch_employee(
                    cursor, employee_id, str(request.base_url).rstrip("/")
                )
        return employee
    finally:
        connection.close()


@app.put("/api/employees/{employee_id}")
async def update_employee(
    request: Request,
    employee_id: int,
    employee_name: str = Form(...),
    department: str = Form(...),
    email: str = Form(...),
    contact_number: str = Form(...),
    designation: str = Form(""),
    address: str = Form(""),
    remove_photo: bool = Form(False),
    photo: Optional[UploadFile] = File(None),
):
    _validate_employee(employee_name, department, email, contact_number)
    image_bytes = await _read_profile_photo(photo)
    embedding = _generate_profile_embedding(image_bytes) if image_bytes else None
    connection = _connect()
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE employees
                    SET employee_name = %s, department = %s,
                        email = %s, contact_number = %s, designation = %s, address = %s
                    WHERE employee_id = %s
                    RETURNING employee_id
                    """,
                    (
                        employee_name.strip(),
                        department.strip(),
                        email.strip(),
                        contact_number.strip(),
                        designation.strip(),
                        address.strip(),
                        employee_id,
                    ),
                )
                if cursor.fetchone() is None:
                    raise HTTPException(status_code=404, detail="Employee not found.")

                if image_bytes is not None:
                    _save_profile_photo(cursor, employee_id, image_bytes, embedding)
                elif remove_photo:
                    cursor.execute(
                        "DELETE FROM employee_faces WHERE employee_id = %s",
                        (employee_id,),
                    )

                employee = _fetch_employee(
                    cursor, employee_id, str(request.base_url).rstrip("/")
                )
        return employee
    finally:
        connection.close()


@app.delete("/api/employees/{employee_id}", status_code=204)
def remove_employee(employee_id: int):
    connection = _connect()
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM employees WHERE employee_id = %s RETURNING employee_id",
                    (employee_id,),
                )
                if cursor.fetchone() is None:
                    raise HTTPException(status_code=404, detail="Employee not found.")
        return Response(status_code=204)
    finally:
        connection.close()
