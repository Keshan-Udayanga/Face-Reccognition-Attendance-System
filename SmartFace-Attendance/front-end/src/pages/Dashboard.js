import { useEffect, useState } from "react";
import {
  ArrowRight,
  BriefcaseBusiness,
  CalendarCheck2,
  CalendarX2,
  CircleAlert,
  Plus,
  UsersRound,
} from "lucide-react";
import { Link } from "react-router";
import EmployeeCard from "../components/EmployeeCard";
import StatCard from "../components/StatCard";
import { getEmployees } from "../services/employeeService";
import "./Dashboard.css";

export default function Dashboard() {
  const [employees, setEmployees] = useState([]);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isCurrent = true;
    getEmployees()
      .then((records) => {
        if (isCurrent) {
          setEmployees(records);
          setError("");
          setIsLoading(false);
        }
      })
      .catch((requestError) => {
        if (isCurrent) {
          setEmployees([]);
          setError(requestError.message);
          setIsLoading(false);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, []);

  const activeCount = employees.filter((employee) => employee.status === "Active").length;
  const presentCount = employees.filter(
    (employee) => employee.attendanceStatus === "Present",
  ).length;
  const absentCount = employees.filter(
    (employee) => employee.attendanceStatus === "Absent",
  ).length;

  return (
    <div className="page-content dashboard-page">
      <section className="welcome-panel">
        <div className="welcome-copy">
          <span className="welcome-eyebrow">YOUR WORKFORCE, AT A GLANCE</span>
          <h2>Welcome back, Admin!</h2>
          <p>Here&apos;s what&apos;s happening with your team today.</p>
        </div>
        <div className="welcome-decoration" aria-hidden="true">
          <span className="welcome-orbit welcome-orbit-one" />
          <span className="welcome-orbit welcome-orbit-two" />
          <div className="welcome-icon">
            <UsersRound size={31} strokeWidth={1.65} />
          </div>
        </div>
        <Link className="welcome-cta" to="/employees/new">
          <Plus aria-hidden="true" size={16} />
          Add employee
        </Link>
      </section>

      {error ? (
        <div className="form-error" role="alert">
          <CircleAlert aria-hidden="true" size={18} />
          <span>{error}</span>
        </div>
      ) : isLoading ? (
        <p role="status">Connecting to the employee database...</p>
      ) : (
        <>
          <section aria-label="Employee statistics" className="stats-grid">
            <StatCard
              icon={BriefcaseBusiness}
              note="Across all departments"
              title="Total Employees"
              tone="blue"
              value={employees.length}
            />
            <StatCard
              icon={UsersRound}
              note="Ready to work"
              title="Active Employees"
              tone="green"
              value={activeCount}
            />
            <StatCard
              icon={CalendarCheck2}
              note="Attendance records not connected"
              title="Today's Present"
              tone="violet"
              value={presentCount}
            />
            <StatCard
              icon={CalendarX2}
              note="Attendance records not connected"
              title="Today's Absent"
              tone="amber"
              value={absentCount}
            />
          </section>

          <section className="recent-section surface-card">
            <div className="section-heading">
              <div>
                <h2>Recent Employees</h2>
                <p>A quick look at the people on your team.</p>
              </div>
              <Link className="primary-button recent-add-button" to="/employees/new">
                <Plus aria-hidden="true" size={16} />
                Add New Employee
              </Link>
            </div>

            {employees.length === 0 ? (
              <div className="empty-state dashboard-empty-state">
                <div className="empty-state-icon">
                  <UsersRound aria-hidden="true" size={22} />
                </div>
                <h3>No employees yet</h3>
                <p>Add your first employee to start managing your team.</p>
                <Link className="primary-button" to="/employees/new">
                  <Plus aria-hidden="true" size={16} />
                  Add your first employee
                </Link>
              </div>
            ) : (
              <>
                <div className="table-scroll">
                  <table className="employee-table dashboard-table">
                    <thead>
                      <tr>
                        <th scope="col">EMPLOYEE</th>
                        <th scope="col">EMPLOYEE ID</th>
                        <th scope="col">DEPARTMENT</th>
                        <th scope="col">EMAIL</th>
                        <th scope="col">STATUS</th>
                      </tr>
                    </thead>
                    <tbody>
                      {employees.slice(0, 5).map((employee) => (
                        <EmployeeCard
                          employee={employee}
                          key={employee.id}
                          showActions={false}
                        />
                      ))}
                    </tbody>
                  </table>
                </div>
                <Link className="view-all-link" to="/employees">
                  View all employees <ArrowRight aria-hidden="true" size={15} />
                </Link>
              </>
            )}
          </section>
        </>
      )}
    </div>
  );
}
