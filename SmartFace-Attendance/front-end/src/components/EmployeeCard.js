import { Eye, Pencil, Trash2 } from "lucide-react";
import "./EmployeeCard.css";

function getInitials(name = "") {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

export default function EmployeeCard({
  employee,
  onView,
  onEdit,
  onDelete,
  showActions = true,
}) {
  const status = employee.status || "Active";

  return (
    <tr>
      <td>
        <div className="employee-name-cell">
          <span className="employee-avatar">
            {employee.photoUrl ? (
              <img alt="" src={employee.photoUrl} />
            ) : (
              getInitials(employee.fullName)
            )}
          </span>
          <span className="employee-name-copy">
            <strong>{employee.fullName}</strong>
            {employee.designation && <span>{employee.designation}</span>}
          </span>
        </div>
      </td>
      <td className="employee-id-cell">{employee.employeeId}</td>
      <td>{employee.department}</td>
      <td className="employee-email-cell">{employee.email}</td>
      <td>
        <span className={`status-badge ${status === "Active" ? "status-active" : "status-inactive"}`}>
          <span />
          {status}
        </span>
      </td>
      {showActions && (
        <td>
          <div className="employee-row-actions">
            <button
              aria-label={`View ${employee.fullName}`}
              className="row-action-button"
              onClick={() => onView(employee)}
              title="View details"
              type="button"
            >
              <Eye aria-hidden="true" size={16} />
            </button>
            <button
              aria-label={`Edit ${employee.fullName}`}
              className="row-action-button"
              onClick={() => onEdit(employee)}
              title="Edit employee"
              type="button"
            >
              <Pencil aria-hidden="true" size={15} />
            </button>
            <button
              aria-label={`Delete ${employee.fullName}`}
              className="row-action-button row-action-delete"
              onClick={() => onDelete(employee)}
              title="Delete employee"
              type="button"
            >
              <Trash2 aria-hidden="true" size={15} />
            </button>
          </div>
        </td>
      )}
    </tr>
  );
}
