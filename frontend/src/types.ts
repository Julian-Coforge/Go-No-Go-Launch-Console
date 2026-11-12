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
