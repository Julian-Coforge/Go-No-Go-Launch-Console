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

export default function ReportList({ reports }: { reports: Report[] }) {
  if (reports.length === 0) return <p>No reports filed yet.</p>;

  return (
    <ul className="report-list" aria-label="Filed reports">
      {reports.map((report) => (
        <li key={report.id} className="report">
          <span className="report-id">#{report.id}</span>{" "}
          <span className="report-who">
            {report.station}, filed by {report.name}
          </span>{" "}
          <strong className={`verdict verdict-${report.verdict}`}>
            {report.verdict === "go" ? "GO" : "NO GO"}
          </strong>{" "}
          <span className="severity">{report.classification.severity} severity</span>{" "}
          <span className={`status status-${report.status}`}>{statusText(report)}</span>
        </li>
      ))}
    </ul>
  );
}
