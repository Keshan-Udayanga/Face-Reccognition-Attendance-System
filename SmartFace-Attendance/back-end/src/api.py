import re
from typing import Optional

import psycopg2
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from database.connection import get_connection

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
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
}
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_PATTERN = re.compile(r"^\+?[\d\s().-]+$")


def _connect():
    connection = get_connection()
    if connection is None:
        raise HTTPException(
            status_code=503,
            detail="Could not connect to PostgreSQL. Check the backend database settings.",
        )
    return connection


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


def _save_profile_photo(cursor, employee_id, image_bytes):
    if image_bytes is None:
        return

    cursor.execute(
        """
        UPDATE employee_faces
        SET face_image = %s,
            face_embedding = 'null'::jsonb,
            model_name = NULL,
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
        (psycopg2.Binary(image_bytes), employee_id),
    )
    if cursor.fetchone() is None:
        cursor.execute(
            """
            INSERT INTO employee_faces (employee_id, face_image, face_embedding, model_name)
            VALUES (%s, %s, 'null'::jsonb, NULL)
            """,
            (employee_id, psycopg2.Binary(image_bytes)),
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
                _save_profile_photo(cursor, employee_id, image_bytes)
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
                    _save_profile_photo(cursor, employee_id, image_bytes)
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
