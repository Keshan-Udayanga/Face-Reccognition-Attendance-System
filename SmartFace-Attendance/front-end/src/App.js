import { useState } from "react";
import { Navigate, Outlet, Route, Routes, useLocation } from "react-router";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import AddEmployee from "./pages/AddEmployee";
import Dashboard from "./pages/Dashboard";
import Employees from "./pages/Employees";

const pageDetails = [
  { path: "/", title: "Dashboard", subtitle: "Welcome back, Admin!" },
  { path: "/employees/new", title: "Add Employee", subtitle: "Add a new team member" },
  { path: "/employees", title: "Employees", subtitle: "Manage your team and employee records" },
  { path: "/attendance", title: "Attendance", subtitle: "Track your team's attendance" },
  { path: "/reports", title: "Reports", subtitle: "Workforce insights and summaries" },
  { path: "/settings", title: "Settings", subtitle: "Manage your workspace preferences" },
];

function AppShell() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const location = useLocation();
  const currentPage =
    location.pathname.includes("/edit")
      ? pageDetails[1]
      : pageDetails.find((page) => page.path === location.pathname) ||
        pageDetails.find((page) => page.path === "/employees");

  return (
    <div className="app-shell">
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
      />
      <div className="main-panel">
        <Header
          onMenuClick={() => setIsSidebarOpen(true)}
          subtitle={currentPage.subtitle}
          title={currentPage.title}
        />
        <Outlet />
      </div>
    </div>
  );
}

function ComingSoon({ title }) {
  return (
    <div className="page-content">
      <section className="surface-card coming-soon-card">
        <div className="empty-state">
          <div className="empty-state-icon">
            <span aria-hidden="true">✦</span>
          </div>
          <h2>{title} is coming soon</h2>
          <p>
            We&apos;re working on this workspace. Employee registration and
            management are ready to use today.
          </p>
        </div>
      </section>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route element={<Dashboard />} index />
        <Route element={<Employees />} path="employees" />
        <Route element={<AddEmployee />} path="employees/new" />
        <Route element={<AddEmployee />} path="employees/:employeeId/edit" />
        <Route element={<ComingSoon title="Attendance" />} path="attendance" />
        <Route element={<ComingSoon title="Reports" />} path="reports" />
        <Route element={<ComingSoon title="Settings" />} path="settings" />
      </Route>
      <Route element={<Navigate replace to="/" />} path="*" />
    </Routes>
  );
}
