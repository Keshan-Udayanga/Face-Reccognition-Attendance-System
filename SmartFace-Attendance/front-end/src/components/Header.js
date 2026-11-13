import { Bell, Menu, Search, UserRound } from "lucide-react";
import "./Header.css";

export default function Header({ title, subtitle, onMenuClick }) {
  const formattedDate = new Intl.DateTimeFormat("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  }).format(new Date());

  return (
    <header className="topbar">
      <div className="topbar-leading">
        <button
          aria-label="Open navigation"
          className="mobile-menu-button"
          onClick={onMenuClick}
          type="button"
        >
          <Menu aria-hidden="true" size={21} />
        </button>
        <div className="topbar-title">
          <h1>{title}</h1>
          {subtitle && <p>{subtitle}</p>}
        </div>
      </div>

      <div className="topbar-actions">
        <div aria-label={formattedDate} className="topbar-date">
          {formattedDate}
        </div>
        <span aria-hidden="true" className="icon-button topbar-search">
          <Search aria-hidden="true" size={19} />
        </span>
        <span aria-hidden="true" className="icon-button notification-button">
          <Bell aria-hidden="true" size={19} />
          <span className="notification-indicator" />
        </span>
        <span aria-hidden="true" className="topbar-divider" />
        <div className="admin-profile">
          <span className="admin-avatar">
            <UserRound aria-hidden="true" size={18} />
          </span>
          <span className="admin-profile-copy">
            <strong>Admin</strong>
            <span>Administrator</span>
          </span>
        </div>
      </div>
    </header>
  );
}
