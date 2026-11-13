ALTER TABLE employees
    DROP CONSTRAINT IF EXISTS employees_employee_code_key,
    DROP COLUMN IF EXISTS employee_code;
