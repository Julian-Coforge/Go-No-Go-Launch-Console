import { type FormEvent, useState } from "react";

import type { CheckResult, FullReport, TraceStep } from "./types";

const CHECK_NAMES: [keyof FullReport["checks"], string][] = [
  ["injection", "Prompt injection"],
  ["missing_details", "Missing details"],
  ["panic", "Panic"],
];

const dollars = (amount: number) => `$${amount.toFixed(6)}`;

function reviewReasons(report: FullReport) {
  const reasons: string[] = [];
  if (report.checks.injection.flagged) reasons.push("Possible prompt injection in the note");
  if (!report.reviewer_approved) reasons.push("The reviewer did not approve the briefing");
  return reasons;
}

function Check({ name, check }: { name: string; check: CheckResult }) {
  return (
    <li className={check.flagged ? "check check-flagged" : "check"}>
      <p>{`${name}: ${check.flagged ? "flagged" : "clear"}. ${check.reason}`}</p>
      {check.missing.length > 0 && <p>{`Missing: ${check.missing.join(", ")}`}</p>}
    </li>
  );
}

function TraceCard({ step }: { step: TraceStep }) {
  return (
    <li className="trace-card">
      <strong>{step.step}</strong>{" "}
      <span>{step.kind === "code" ? "plain code" : step.model}</span>{" "}
      <span>{`${step.input_tokens} in / ${step.output_tokens} out tokens`}</span>{" "}
      <span>{dollars(step.cost_usd)}</span>{" "}
      {step.fallback && <em className="fallback">fell back</em>}
      <p className="trace-summary">{step.summary}</p>
    </li>
  );
}

function ApproveForm({
  report,
  onApproved,
}: {
  report: FullReport;
  onApproved: (report: FullReport) => void;
}) {
  const [approver, setApprover] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSending(true);
    setError(null);
    try {
      const response = await fetch(`/api/reports/${report.id}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approver_name: approver }),
      });
      const body = await response.json();
      if (response.ok) onApproved(body);
      else if (Array.isArray(body.errors))
        setError(body.errors.map((e: { message: string }) => e.message).join(" "));
      else setError(body.detail ?? `The API returned an error (${response.status})`);
    } catch {
      setError("Could not reach the API");
    } finally {
      setSending(false);
    }
  }

  return (
    <form onSubmit={submit} aria-label="Approve report">
      <label htmlFor="approver-name">Flight Director name</label>
      <input
        id="approver-name"
        value={approver}
        required
        maxLength={100}
        onChange={(event) => setApprover(event.target.value)}
      />
      <button type="submit" disabled={sending}>
        Approve
      </button>
      {error && <p role="alert">{error}</p>}
    </form>
  );
}

export default function ReportDetail({
  report,
  onApproved,
}: {
  report: FullReport;
  onApproved: (report: FullReport) => void;
}) {
  const reasons = report.status === "needs_review" ? reviewReasons(report) : [];

  return (
    <article className="report-detail" aria-labelledby="detail-heading">
      <h2 id="detail-heading">Report #{report.id}</h2>
      <p>
        {report.station}, filed by {report.name}
      </p>
      <p className={`verdict verdict-${report.verdict}`}>
        <strong>{report.verdict === "go" ? "GO" : "NO GO"}</strong>
      </p>
      {report.violations.length > 0 && (
        <ul aria-label="Limit violations">
          {report.violations.map((violation) => (
            <li key={violation.field}>{violation.message}</li>
          ))}
        </ul>
      )}
      <p>{`Brief by: ${report.brief_by_minutes} minutes`}</p>
      <p>{`${report.classification.subsystem}, ${report.classification.severity} severity`}</p>

      {reasons.length > 0 && (
        <div role="alert" className="needs-review">
          <strong>Needs review.</strong> {reasons.join(". ")}.
        </div>
      )}

      <h3>Briefing</h3>
      <p className="briefing">{report.briefing}</p>

      <h3>Engineer's note</h3>
      <p className="note">{report.note}</p>

      <h3>Checks</h3>
      <ul aria-label="Checks">
        {CHECK_NAMES.map(([key, name]) => (
          <Check key={key} name={name} check={report.checks[key]} />
        ))}
      </ul>

      <h3>Trace</h3>
      <ol aria-label="Pipeline trace">
        {report.trace.map((step, index) => (
          <TraceCard key={`${step.step}-${index}`} step={step} />
        ))}
      </ol>
      <p>{`Total cost: ${dollars(report.total_cost_usd)}`}</p>

      <h3>Approval</h3>
      {report.status === "approved" ? (
        <p>
          Approved by {report.approved_by}
          {report.approved_at && ` at ${new Date(report.approved_at).toLocaleString()}`}
        </p>
      ) : (
        <ApproveForm report={report} onApproved={onApproved} />
      )}
    </article>
  );
}
