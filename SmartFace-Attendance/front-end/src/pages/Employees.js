import { useEffect, useMemo, useState } from "react";
import {
  CircleAlert,
  Search,
  UserRoundPlus,
  UsersRound,
  X,
} from "lucide-react";
import { useLocation, useNavigate } from "react-router";
import EmployeeCard from "../components/EmployeeCard";
import { deleteEmployee, getEmployees } from "../services/employeeService";
import "./Employees.css";

function getInitials(name = "") {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

export default function Employees() {
  const [employees, setEmployees] = useState([]);
  const [search, setSearch] = useState("");
  const [department, setDepartment] = useState("All departments");
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    if (location.state?.notice) {
      setNotice(location.state.notice);
      navigate(location.pathname, { replace: true, state: null });
    }

    let isCurrent = true;
    getEmployees()
      .then((records) => {
        if (isCurrent) {
          setEmployees(records);
          setError("");
          setIsLoading(false);
        }
      })
      .catch((loadError) => {
        if (isCurrent) {
          setEmployees([]);
          setError(loadError.message);
          setIsLoading(false);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [location.pathname, location.state, navigate]);

  const departments = useMemo(
    () =>
      [...new Set(employees.map((employee) => employee.department))]
        .filter(Boolean)
        .sort((first, second) => first.localeCompare(second)),
    [employees],
  );

  const filteredEmployees = useMemo(() => {
    const normalizedSearch = search.trim().toLocaleLowerCase();
    return employees.filter((employee) => {
      const matchesSearch =
        !normalizedSearch ||
        employee.fullName.toLocaleLowerCase().includes(normalizedSearch) ||
        employee.employeeId.toLocaleLowerCase().includes(normalizedSearch);
      const matchesDepartment =
        department === "All departments" || employee.department === department;
      return matchesSearch && matchesDepartment;
    });
  }, [department, employees, search]);

  async function handleDelete(employee) {
    const confirmed = window.confirm(
      `Delete ${employee.fullName}? This cannot be undone.`,
    );
    if (!confirmed) {
      return;
    }

    try {
      await deleteEmployee(employee.id);
      setEmployees(await getEmployees());
      setSelectedEmployee(null);
      setError("");
    } catch (deleteError) {
      setError(deleteError.message);
    }
  }

  function handleEdit(employee) {
    navigate(`/employees/${encodeURIComponent(employee.id)}/edit`);
  }

  return (
    <div className="page-content employees-page">
      {notice && (
        <div className="success-banner" role="status">
          <span className="success-banner-check">✓</span>
          {notice}
          <button
            aria-label="Dismiss notification"
            className="dismiss-notice"
            onClick={() => setNotice("")}
            type="button"
          >
            <X aria-hidden="true" size={16} />
          </button>
        </div>
      )}

      {error ? (
        <div className="form-error" role="alert">
          <CircleAlert aria-hidden="true" size={18} />
          <span>{error}</span>
        </div>
      ) : isLoading ? (
        <p role="status">Connecting to the employee database...</p>
      ) : (
        <>
          <section className="employees-toolbar surface-card">
            <div className="employees-toolbar-copy">
              <div className="employees-toolbar-icon">
                <UsersRound aria-hidden="true" size={19} />
              </div>
              <div>
                <h2>All Employees</h2>
                <p>
                  {employees.length} {employees.length === 1 ? "person" : "people"} in your
                  workforce
                </p>
              </div>
            </div>
            <button
              className="primary-button"
              onClick={() => navigate("/employees/new")}
              type="button"
            >
              <UserRoundPlus aria-hidden="true" size={16} />
              Add Employee
            </button>
          </section>

          <section className="employees-list-card surface-card">
            <div className="employee-filter-bar">
              <label className="employee-search">
                <Search aria-hidden="true" size={17} />
                <span className="visually-hidden">Search by name or employee ID</span>
                <input
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search name or employee ID..."
                  type="search"
                  value={search}
                />
              </label>
              <label className="department-filter">
                <span className="visually-hidden">Filter by department</span>
                <select
                  onChange={(event) => setDepartment(event.target.value)}
                  value={department}
                >
                  <option>All departments</option>
                  {departments.map((name) => (
                    <option key={name}>{name}</option>
                  ))}
                </select>
              </label>
              <span aria-live="polite" className="filter-result-count">
                {filteredEmployees.length} shown
              </span>
            </div>

            {employees.length === 0 ? (
              <div className="empty-state employees-empty-state">
                <div className="empty-state-icon">
                  <UsersRound aria-hidden="true" size={22} />
                </div>
                <h3>No employees yet</h3>
                <p>Your new team members will appear here after you add them.</p>
                <button
                  className="primary-button"
                  onClick={() => navigate("/employees/new")}
                  type="button"
                >
                  <UserRoundPlus aria-hidden="true" size={16} />
                  Add your first employee
                </button>
              </div>
            ) : filteredEmployees.length === 0 ? (
              <div className="empty-state employees-empty-state">
                <div className="empty-state-icon">
                  <Search aria-hidden="true" size={21} />
                </div>
                <h3>No matching employees</h3>
                <p>Try a different name, employee ID, or department filter.</p>
                <button
                  className="secondary-button"
                  onClick={() => {
                    setSearch("");
                    setDepartment("All departments");
                  }}
                  type="button"
                >
                  Clear filters
                </button>
              </div>
            ) : (
              <div className="table-scroll">
                <table className="employee-table employees-table">
                  <thead>
                    <tr>
                      <th scope="col">EMPLOYEE</th>
                      <th scope="col">EMPLOYEE ID</th>
                      <th scope="col">DEPARTMENT</th>
                      <th scope="col">EMAIL</th>
                      <th scope="col">STATUS</th>
                      <th className="actions-heading" scope="col">
                        ACTIONS
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredEmployees.map((employee) => (
                      <EmployeeCard
                        employee={employee}
                        key={employee.id}
                        onDelete={handleDelete}
                        onEdit={handleEdit}
                        onView={setSelectedEmployee}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}

      {selectedEmployee && (
        <div
          className="employee-modal-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setSelectedEmployee(null);
            }
          }}
        >
          <section
            aria-labelledby="employee-details-title"
            aria-modal="true"
            className="employee-details-modal"
            role="dialog"
          >
            <div className="employee-modal-heading">
              <div>
                <span className="modal-eyebrow">EMPLOYEE PROFILE</span>
                <h2 id="employee-details-title">Employee details</h2>
              </div>
              <button
                aria-label="Close employee details"
                className="row-action-button"
                onClick={() => setSelectedEmployee(null)}
                type="button"
              >
                <X aria-hidden="true" size={19} />
              </button>
            </div>
            <div className="employee-detail-profile">
              <span className="employee-detail-avatar">
                {selectedEmployee.photoUrl ? (
                  <img alt="" src={selectedEmployee.photoUrl} />
                ) : (
                  getInitials(selectedEmployee.fullName)
                )}
              </span>
              <div>
                <h3>{selectedEmployee.fullName}</h3>
                <p>{selectedEmployee.designation || "Team member"}</p>
                <span
                  className={`status-badge ${selectedEmployee.status === "Active" ? "status-active" : "status-inactive"}`}
                >
                  <span />
                  {selectedEmployee.status || "Active"}
                </span>
              </div>
            </div>
            <dl className="employee-details-grid">
              <div>
                <dt>Employee ID</dt>
                <dd>{selectedEmployee.employeeId}</dd>
              </div>
              <div>
                <dt>Department</dt>
                <dd>{selectedEmployee.department}</dd>
              </div>
              <div>
                <dt>Email address</dt>
                <dd>{selectedEmployee.email}</dd>
              </div>
              <div>
                <dt>Contact number</dt>
                <dd>{selectedEmployee.contactNumber}</dd>
              </div>
              <div className="employee-detail-full">
                <dt>Address</dt>
                <dd>{selectedEmployee.address || "Not provided"}</dd>
              </div>
            </dl>
            <div className="employee-modal-actions">
              <button
                className="secondary-button"
                onClick={() => setSelectedEmployee(null)}
                type="button"
              >
                Close
              </button>
              <button
                className="primary-button"
                onClick={() => handleEdit(selectedEmployee)}
                type="button"
              >
                Edit employee
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
