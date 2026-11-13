import {
  BarChart3,
  CalendarCheck2,
  LayoutDashboard,
  ScanFace,
  Settings2,
  UserRoundPlus,
  UsersRound,
} from "lucide-react";
import { NavLink, useLocation } from "react-router";
import "./Sidebar.css";

const navigationItems = [
  { label: "Dashboard", path: "/", icon: LayoutDashboard },
  { label: "Employees", path: "/employees", icon: UsersRound },
  { label: "Add Employee", path: "/employees/new", icon: UserRoundPlus },
  { label: "Attendance", path: "/attendance", icon: CalendarCheck2 },
  { label: "Reports", path: "/reports", icon: BarChart3 },
  { label: "Settings", path: "/settings", icon: Settings2 },
];

export default function Sidebar({ isOpen, onClose }) {
  const location = useLocation();

  function isItemActive(path) {
    if (path === "/") {
      return location.pathname === "/";
    }

    if (path === "/employees") {
      return (
        location.pathname === "/employees" ||
        location.pathname.startsWith("/employees/") &&
          location.pathname !== "/employees/new"
      );
    }

    return location.pathname === path;
  }

  return (
    <>
      {isOpen && (
        <button
          aria-label="Close navigation"
          className="sidebar-backdrop"
          onClick={onClose}
          type="button"
        />
      )}
      <aside className={`sidebar ${isOpen ? "sidebar-open" : ""}`}>
        <NavLink
          aria-label="SmartFace dashboard"
          className="brand"
          onClick={onClose}
          to="/"
        >
          <span className="brand-mark">
            <ScanFace aria-hidden="true" size={23} strokeWidth={2.2} />
          </span>
          <span className="brand-copy">
            <strong>SmartFace</strong>
            <span>WORKFORCE SUITE</span>
          </span>
        </NavLink>

        <div className="sidebar-section-label">WORKSPACE</div>
        <nav aria-label="Main navigation" className="sidebar-nav">
          {navigationItems.map(({ label, path, icon: Icon }) => (
            <NavLink
              aria-current={isItemActive(path) ? "page" : undefined}
              className={`sidebar-link ${isItemActive(path) ? "sidebar-link-active" : ""}`}
              key={path}
              onClick={onClose}
              to={path}
            >
              <Icon aria-hidden="true" size={19} strokeWidth={1.9} />
              <span>{label}</span>
              {label === "Add Employee" && <span className="sidebar-link-dot" />}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-footer-icon">
            <ScanFace aria-hidden="true" size={20} />
          </div>
          <div>
            <strong>SmartFace Admin</strong>
            <span>Attendance &amp; people</span>
          </div>
        </div>
      </aside>
    </>
  );
}
