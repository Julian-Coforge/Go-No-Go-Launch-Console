import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import App from "./App";
import { fullReport } from "./fixtures";

type Routes = Record<string, () => Promise<Response>>;

const never = () => new Promise<Response>(() => {});
const ok = (body: unknown, status = 200) => () =>
  Promise.resolve(new Response(JSON.stringify(body), { status }));

const STORED = {
  id: 1,
  name: "Ada Lovelace",
  station: "Pad 39A",
  verdict: "go",
  status: "pending_approval",
  classification: { subsystem: "weather", severity: "low", rationale: "" },
  created_at: "2026-11-12T16:00:00+00:00",
  approved_by: null,
};

// Answers each request by method and URL, e.g. "GET /api/reports".
function stubApi(routes: Routes) {
  const fetchMock = vi.fn((url: string, init?: RequestInit) => {
    const handler = routes[`${init?.method ?? "GET"} ${url}`];
    return handler ? handler() : never();
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function fileAReport() {
  const values: Record<string, string> = {
    Name: "Grace Hopper",
    Station: "Pad 40",
    "Wind (knots)": "10",
    "Temperature (°C)": "15",
    "Fuel (%)": "98",
    Note: "Ready.",
  };
  for (const [label, value] of Object.entries(values)) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
  }
  fireEvent.click(screen.getByRole("button", { name: "File report" }));
}

describe("App", () => {
  it("shows the Mission Control title", () => {
    stubApi({});
    render(<App />);
    expect(screen.getByRole("heading", { name: "Mission Control" })).toBeInTheDocument();
  });

  it("shows the API as online when /api/health answers ok", async () => {
    stubApi({ "GET /api/health": ok({ status: "ok" }) });
    render(<App />);
    expect(await screen.findByText("API online")).toBeInTheDocument();
  });

  it("shows the API as offline when /api/health cannot be reached", async () => {
    stubApi({ "GET /api/health": () => Promise.reject(new TypeError("Failed to fetch")) });
    render(<App />);
    expect(await screen.findByText("API offline")).toBeInTheDocument();
  });

  it("asks the back end through the /api proxy", () => {
    const fetchMock = stubApi({});
    render(<App />);
    expect(fetchMock).toHaveBeenCalledWith("/api/health");
  });

  it("shows the report form", () => {
    stubApi({});
    render(<App />);
    expect(screen.getByRole("button", { name: "File report" })).toBeInTheDocument();
  });

  it("loads the filed reports", async () => {
    stubApi({ "GET /api/reports": ok([STORED]) });
    render(<App />);
    expect(await screen.findByText(/Pad 39A/)).toBeInTheDocument();
  });

  it("says so when the reports cannot be loaded", async () => {
    stubApi({ "GET /api/reports": () => Promise.reject(new TypeError("Failed to fetch")) });
    render(<App />);
    expect(await screen.findByText("Could not load reports.")).toBeInTheDocument();
  });

  it("puts a newly filed report at the top of the list", async () => {
    stubApi({
      "GET /api/reports": ok([STORED]),
      "POST /api/reports": ok({ ...STORED, id: 2, station: "Pad 40" }, 201),
    });
    render(<App />);
    await screen.findByText(/Pad 39A/);
    fileAReport();
    await screen.findByText(/Pad 40/);
    expect(screen.getAllByRole("listitem")[0]).toHaveTextContent("#2");
  });

  it("opens a report's details from the list", async () => {
    stubApi({
      "GET /api/reports": ok([STORED]),
      "GET /api/reports/1": ok(fullReport()),
    });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Open report #1" }));
    expect(await screen.findByRole("heading", { name: "Report #1" })).toBeInTheDocument();
  });

  it("shows an approval in the list straight away", async () => {
    stubApi({
      "GET /api/reports": ok([STORED]),
      "GET /api/reports/1": ok(fullReport()),
      "POST /api/reports/1/approve": ok(fullReport({ status: "approved", approved_by: "Gene Kranz" })),
    });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Open report #1" }));
    fireEvent.change(await screen.findByLabelText("Flight Director name"), { target: { value: "Gene Kranz" } });
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    const list = screen.getByRole("list", { name: "Filed reports" });
    expect(await within(list).findByText("Approved by Gene Kranz")).toBeInTheDocument();
  });
});
