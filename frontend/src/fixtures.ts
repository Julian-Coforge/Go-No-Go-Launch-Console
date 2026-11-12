import type { FullReport, TraceStep } from "./types";

// A stored report as GET /api/reports/{id} returns it, for tests.

export function traceStep(overrides: Partial<TraceStep> = {}): TraceStep {
  return {
    step: "classify",
    kind: "model",
    model: "claude-haiku-5-5",
    input_tokens: 100,
    output_tokens: 50,
    cost_usd: 0.000035,
    fallback: false,
    summary: "propulsion / low",
    ...overrides,
  };
}

const clear = (step: string) => ({ step, flagged: false, reason: "Nothing found.", missing: [], fallback: false });

export function fullReport(overrides: Partial<FullReport> = {}): FullReport {
  return {
    id: 1,
    name: "Ada Lovelace",
    station: "Pad 39A",
    wind_knots: 12.5,
    temp_c: 18,
    fuel_pct: 99,
    note: "All readings nominal.",
    verdict: "go",
    violations: [],
    status: "pending_approval",
    classification: { subsystem: "weather", severity: "low", rationale: "Calm." },
    brief_by_minutes: 30,
    checks: {
      injection: clear("check_injection"),
      missing_details: clear("check_missing_details"),
      panic: clear("check_panic"),
    },
    rounds: [{ round: 1, approved: true, feedback: "Clear." }],
    briefing: "GO for launch. All readings within limits.",
    reviewer_approved: true,
    trace: [
      traceStep(),
      traceStep({ step: "limits", kind: "code", model: null, input_tokens: 0, output_tokens: 0, cost_usd: 0, summary: "go" }),
    ],
    total_cost_usd: 0.00294,
    created_at: "2026-11-12T16:00:00+00:00",
    approved_by: null,
    approved_at: null,
    ...overrides,
  };
}
