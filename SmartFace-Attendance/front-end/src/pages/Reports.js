import { useEffect, useState } from "react";
import {
  AlertCircle,
  CalendarDays,
  Download,
  FileSpreadsheet,
  Filter,
  FolderOpen,
  LoaderCircle,
  RotateCcw,
} from "lucide-react";
import {
  getAttendanceMonthDownloadUrl,
  getAttendanceMonths,
} from "../services/attendanceService";
import "./Reports.css";

const MONTH_OPTIONS = Array.from({ length: 12 }, (_, index) => {
  const date = new Date(2024, index, 1);
  return {
    value: String(index + 1).padStart(2, "0"),
    label: new Intl.DateTimeFormat("en-US", { month: "long" }).format(date),
  };
});

function formatMonth(value) {
  const [year, month] = value.split("-").map(Number);
  return new Intl.DateTimeFormat("en-US", {
    month: "long",
    year: "numeric",
  }).format(new Date(year, month - 1, 1));
}

export default function Reports() {
  const [availableMonths, setAvailableMonths] = useState([]);
  const [selectedYear, setSelectedYear] = useState("all");
  const [selectedMonth, setSelectedMonth] = useState("all");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isCurrent = true;

    getAttendanceMonths()
      .then((months) => {
        if (!Array.isArray(months)) {
          throw new Error("The attendance archive returned an invalid month list.");
        }
        if (
          months.some(
            (month) =>
              typeof month !== "string" ||
              !/^\d{4}-(0[1-9]|1[0-2])$/.test(month),
          )
        ) {
          throw new Error("The attendance archive returned an invalid month list.");
        }
        if (isCurrent) {
          setAvailableMonths(
            [...new Set(months)].sort((first, second) =>
              second.localeCompare(first),
            ),
          );
          setError("");
          setIsLoading(false);
        }
      })
      .catch((requestError) => {
        if (isCurrent) {
          setAvailableMonths([]);
          setError(requestError.message);
          setIsLoading(false);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, []);

  const years = [...new Set(availableMonths.map((month) => month.slice(0, 4)))].sort(
    (first, second) => second.localeCompare(first),
  );
  const filteredMonths = availableMonths.filter((month) => {
    const [year, monthNumber] = month.split("-");
    return (
      (selectedYear === "all" || year === selectedYear) &&
      (selectedMonth === "all" || monthNumber === selectedMonth)
    );
  });

  function clearFilters() {
    setSelectedYear("all");
    setSelectedMonth("all");
  }

  return (
    <div className="page-content reports-page">
      <section className="reports-overview">
        <div className="reports-overview-copy">
          <span className="reports-overview-eyebrow">ATTENDANCE ARCHIVE</span>
          <h2>Monthly attendance reports</h2>
          <p>Browse and download your attendance records as CSV files.</p>
        </div>
        <div aria-hidden="true" className="reports-overview-icon">
          <FileSpreadsheet size={28} strokeWidth={1.7} />
        </div>
      </section>

      {error && (
        <div className="form-error" role="alert">
          <AlertCircle aria-hidden="true" size={18} />
          <span>{error}</span>
        </div>
      )}

      <section aria-label="Monthly attendance CSV files" className="reports-panel surface-card">
        <div className="reports-panel-heading">
          <div className="reports-panel-title">
            <span className="reports-panel-icon">
              <CalendarDays aria-hidden="true" size={19} />
            </span>
            <div>
              <h2>Attendance files</h2>
              <p>Each CSV contains records for one calendar month.</p>
            </div>
          </div>
          <span className="reports-file-count">
            {isLoading
              ? "Loading"
              : error
                ? "Unavailable"
                : `${filteredMonths.length} ${filteredMonths.length === 1 ? "file" : "files"}`}
          </span>
        </div>

        <div aria-label="Filter attendance files" className="reports-filters">
          <label className="reports-filter">
            <span>Year</span>
            <select
              aria-label="Filter by year"
              onChange={(event) => setSelectedYear(event.target.value)}
              value={selectedYear}
            >
              <option value="all">All years</option>
              {years.map((year) => (
                <option key={year} value={year}>
                  {year}
                </option>
              ))}
            </select>
          </label>

          <label className="reports-filter">
            <span>Month</span>
            <select
              aria-label="Filter by month"
              onChange={(event) => setSelectedMonth(event.target.value)}
              value={selectedMonth}
            >
              <option value="all">All months</option>
              {MONTH_OPTIONS.map((month) => (
                <option key={month.value} value={month.value}>
                  {month.label}
                </option>
              ))}
            </select>
          </label>

          <button
            className="secondary-button reports-clear-button"
            disabled={selectedYear === "all" && selectedMonth === "all"}
            onClick={clearFilters}
            type="button"
          >
            <RotateCcw aria-hidden="true" size={15} />
            Clear filters
          </button>
        </div>

        {isLoading ? (
          <div className="reports-state" role="status">
            <LoaderCircle aria-hidden="true" className="reports-loader" size={23} />
            <span>Loading monthly attendance files...</span>
          </div>
        ) : error ? (
          <div className="reports-state reports-empty-state" role="status">
            <span className="reports-empty-icon">
              <FolderOpen aria-hidden="true" size={23} />
            </span>
            <strong>Attendance files are unavailable</strong>
            <span>Check the attendance service and try again later.</span>
          </div>
        ) : filteredMonths.length === 0 ? (
          <div className="reports-state reports-empty-state" role="status">
            <span className="reports-empty-icon">
              <FolderOpen aria-hidden="true" size={23} />
            </span>
            <strong>{availableMonths.length === 0 ? "No attendance files yet" : "No files match these filters"}</strong>
            <span>
              {availableMonths.length === 0
                ? "Monthly CSV files will appear here as attendance is recorded."
                : "Try selecting another month or year."}
            </span>
          </div>
        ) : (
          <ul className="reports-file-list">
            {filteredMonths.map((month) => (
              <li className="reports-file-row" key={month}>
                <span className="reports-file-icon">
                  <FileSpreadsheet aria-hidden="true" size={20} />
                </span>
                <div className="reports-file-copy">
                  <strong>{formatMonth(month)}</strong>
                  <span>attendance_{month}.csv</span>
                </div>
                <a
                  className="primary-button reports-download-button"
                  download={`attendance_${month}.csv`}
                  href={getAttendanceMonthDownloadUrl(month)}
                >
                  <Download aria-hidden="true" size={16} />
                  Download CSV
                </a>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
