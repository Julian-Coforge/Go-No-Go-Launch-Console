import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ReportList from "./ReportList";
import type { Report } from "./types";

function report(overrides: Partial<Report> = {}): Report {
  return {
    id: 1,
    name: "Ada Lovelace",
    station: "Pad 39A",
    verdict: "go",
    status: "pending_approval",
    classification: { subsystem: "weather", severity: "low", rationale: "calm" },
    created_at: "2026-11-12T16:39:15+00:00",
    approved_by: null,
    ...overrides,
  };
}

describe("ReportList", () => {
  it("says so when no reports are filed", () => {
    render(<ReportList reports={[]} />);
    expect(screen.getByText("No reports filed yet.")).toBeInTheDocument();
  });

  it("shows one item per report", () => {
    render(<ReportList reports={[report({ id: 2 }), report({ id: 1 })]} />);
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
  });

  it("keeps the order it is given (newest first from the API)", () => {
    render(<ReportList reports={[report({ id: 2 }), report({ id: 1 })]} />);
    expect(screen.getAllByRole("listitem")[0]).toHaveTextContent("#2");
  });

  it("shows the station", () => {
    render(<ReportList reports={[report({ station: "Pad 40" })]} />);
    expect(screen.getByText(/Pad 40/)).toBeInTheDocument();
  });

  it("shows the name of who filed it", () => {
    render(<ReportList reports={[report({ name: "Grace Hopper" })]} />);
    expect(screen.getByText(/Grace Hopper/)).toBeInTheDocument();
  });

  it("shows a GO verdict", () => {
    render(<ReportList reports={[report({ verdict: "go" })]} />);
    expect(screen.getByText("GO")).toBeInTheDocument();
  });

  it("shows a NO GO verdict", () => {
    render(<ReportList reports={[report({ verdict: "no_go" })]} />);
    expect(screen.getByText("NO GO")).toBeInTheDocument();
  });

  it("shows the severity", () => {
    render(<ReportList reports={[report({ classification: { subsystem: "avionics", severity: "high", rationale: "" } })]} />);
    expect(screen.getByText(/high severity/)).toBeInTheDocument();
  });

  it.each([
    ["pending_approval", "Pending approval"],
    ["needs_review", "Needs review"],
  ] as const)("shows the %s status in words", (status, words) => {
    render(<ReportList reports={[report({ status })]} />);
    expect(screen.getByText(words)).toBeInTheDocument();
  });

  it("shows who approved an approved report", () => {
    render(<ReportList reports={[report({ status: "approved", approved_by: "Gene Kranz" })]} />);
    expect(screen.getByText("Approved by Gene Kranz")).toBeInTheDocument();
  });

  it("labels the list for screen readers", () => {
    render(<ReportList reports={[report()]} />);
    expect(within(screen.getByRole("list", { name: "Filed reports" })).getAllByRole("listitem")).toHaveLength(1);
  });
});
