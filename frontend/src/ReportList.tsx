import type { Report, ReportStatus } from "./types";

const STATUS_TEXT: Record<Exclude<ReportStatus, "approved">, string> = {
  pending_approval: "Pending approval",
  needs_review: "Needs review",
};

function statusText(report: Report) {
  return report.status === "approved"
    ? `Approved by ${report.approved_by}`
    : STATUS_TEXT[report.status];
}

export default function ReportList({
  reports,
  onSelect,
}: {
  reports: Report[];
  onSelect?: (id: number) => void;
}) {
  if (reports.length === 0) return <p className="muted">No reports filed yet.</p>;

  return (
    <ul className="report-list" aria-label="Filed reports">
      {reports.map((report) => (
        <li key={report.id} className="report">
          <div className="report-main">
            <span className="report-id">#{report.id}</span>{" "}
            <span className="report-who">
              {report.station}, filed by {report.name}
            </span>
          </div>{" "}
          <div className="report-tags">
            <strong className={`badge verdict verdict-${report.verdict}`}>
              {report.verdict === "go" ? "GO" : "NO GO"}
            </strong>{" "}
            <span className={`badge severity severity-${report.classification.severity}`}>
              {report.classification.severity} severity
            </span>{" "}
            <span className={`badge status status-${report.status}`}>{statusText(report)}</span>
            {onSelect && (
              <>
                {" "}
                <button type="button" className="button-secondary" onClick={() => onSelect(report.id)}>
                  Open report #{report.id}
                </button>
              </>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}
