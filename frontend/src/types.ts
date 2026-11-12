// The parts of a stored report (GET /reports) that the UI reads.

export type Verdict = "go" | "no_go";
export type ReportStatus = "pending_approval" | "needs_review" | "approved";

export type Classification = {
  subsystem: string;
  severity: "high" | "medium" | "low";
  rationale: string;
};

export type Report = {
  id: number;
  name: string;
  station: string;
  verdict: Verdict;
  status: ReportStatus;
  classification: Classification;
  created_at: string;
  approved_by: string | null;
};

export type Violation = { field: string; value: number; limit: number; message: string };

export type CheckResult = {
  step: string;
  flagged: boolean;
  reason: string;
  missing: string[];
  fallback: boolean;
};

export type BriefingRound = { round: number; approved: boolean; feedback: string };

export type TraceStep = {
  step: string;
  kind: "model" | "code";
  model: string | null;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  fallback: boolean;
  summary: string;
};

// A stored report as GET /reports/{id} returns it.
export type FullReport = Report & {
  wind_knots: number;
  temp_c: number;
  fuel_pct: number;
  note: string;
  violations: Violation[];
  brief_by_minutes: number;
  checks: { injection: CheckResult; missing_details: CheckResult; panic: CheckResult };
  rounds: BriefingRound[];
  briefing: string;
  reviewer_approved: boolean;
  trace: TraceStep[];
  total_cost_usd: number;
  approved_at: string | null;
};
