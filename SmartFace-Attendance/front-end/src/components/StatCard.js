import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import "./StatCard.css";

export default function StatCard({
  title,
  value,
  note,
  icon: Icon,
  tone = "blue",
  trend,
}) {
  return (
    <article className="stat-card surface-card">
      <div className={`stat-icon stat-icon-${tone}`}>
        <Icon aria-hidden="true" size={20} strokeWidth={1.9} />
      </div>
      <div className="stat-card-title">{title}</div>
      <div className="stat-card-value">{value}</div>
      <div className="stat-card-footer">
        {trend && (
          <span className={`stat-trend ${trend.direction === "down" ? "stat-trend-down" : ""}`}>
            {trend.direction === "down" ? (
              <ArrowDownRight aria-hidden="true" size={14} />
            ) : (
              <ArrowUpRight aria-hidden="true" size={14} />
            )}
            {trend.label}
          </span>
        )}
        {note && <span className="stat-note">{note}</span>}
      </div>
    </article>
  );
}
