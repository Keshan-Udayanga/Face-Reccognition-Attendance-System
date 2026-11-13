# SmartFace – AI-Powered Attendance & Overtime Management System

The React admin dashboard is in [`front-end/`](./front-end). The Python
backend, database scripts, and Python environment are grouped in
[`back-end/`](./back-end). Employee records and profile photos are stored in
PostgreSQL through the FastAPI service in `back-end/src/api.py`.

## Start the application

The backend must be running to view or change employee records. Start it in one
PowerShell terminal:

```powershell
cd E:\Face-Recognition-Attendance-System\SmartFace-Attendance\back-end
.\venv\Scripts\Activate.ps1
uvicorn src.api:app --reload
```

In a second terminal, start the frontend. This opens the dashboard in your
default browser:

```powershell
cd E:\Face-Recognition-Attendance-System\SmartFace-Attendance\front-end
npm start
```

The API is available at `http://127.0.0.1:8000/api`. If the backend is not
running, the dashboard and employee list show an API connection error instead
of employee data or misleading zero counts.

The existing database connection uses the `DB_HOST`, `DB_PORT`, `DB_NAME`,
`DB_USER`, and `DB_PASSWORD` values in `back-end/.env`. Keep this file private;
never put database credentials in frontend code.

The employee-details migration is
`back-end/database/migrations/001_add_employee_contact_details.sql`. It adds email,
contact number, designation, and address columns to the existing `employees`
table. It has already been applied to the configured PostgreSQL database.
Apply it through pgAdmin's Query Tool before starting the API against a
different database.

The migration
`back-end/database/migrations/002_use_auto_generated_employee_id.sql` removes the
duplicate `employee_code` column. Employee IDs come from PostgreSQL's existing
auto-generated `employees.employee_id`. Admins do not type or edit IDs; the
generated ID is displayed in the employee list and after registration.

## Employee and profile-photo data

Employee details are stored in `employees`. Uploaded JPG and PNG profile
photos (maximum 1 MB) are stored as PostgreSQL `BYTEA` in `employee_faces`.
Creating or editing an employee and their photo runs in a single database
transaction. Deleting an employee also deletes their face records through the
existing cascading foreign key.

Face recognition and embedding generation are not implemented. The required
`face_embedding` column is set to JSON `null` until a later recognition
feature generates a real embedding. Attendance statistics show zero because
no attendance records are connected yet.

## Project structure

```text
SmartFace-Attendance/
├── back-end/
│   ├── config/
│   ├── data/
│   ├── database/
│   │   ├── connection.py
│   │   └── migrations/
│   │       ├── 001_add_employee_contact_details.sql
│   │       └── 002_use_auto_generated_employee_id.sql
│   ├── n8n/
│   ├── notebooks/
│   ├── reports/
│   ├── src/
│   │   └── api.py
│   ├── tests/
│   ├── venv/
│   ├── test_camera.py
│   ├── test_database.py
│   ├── test_environment.py
│   ├── .gitignore
│   ├── .env
│   └── requirements.txt
├── front-end/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── assets/
│   │   │   └── images/
│   │   │       └── .gitkeep
│   │   ├── components/
│   │   │   ├── EmployeeCard.js
│   │   │   ├── EmployeeCard.css
│   │   │   ├── Header.js
│   │   │   ├── Header.css
│   │   │   ├── Sidebar.js
│   │   │   ├── Sidebar.css
│   │   │   ├── StatCard.js
│   │   │   └── StatCard.css
│   │   ├── pages/
│   │   │   ├── AddEmployee.js
│   │   │   ├── AddEmployee.css
│   │   │   ├── Dashboard.js
│   │   │   ├── Dashboard.css
│   │   │   ├── Employees.js
│   │   │   └── Employees.css
│   │   ├── services/
│   │   │   └── employeeService.js
│   │   ├── styles/
│   │   │   ├── global.css
│   │   │   └── variables.css
│   │   ├── App.js
│   │   └── index.js
│   ├── .gitignore
│   ├── package.json
│   └── package-lock.json
└── README.md
```
