import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import ReportForm from "./ReportForm";

const FILLED = {
  Name: "Ada Lovelace",
  Station: "Pad 39A",
  "Wind (knots)": "12.5",
  "Temperature (°C)": "18",
  "Fuel (%)": "99",
  Note: "All readings nominal.",
};

function stubFetch(response: Promise<Response>) {
  const fetchMock = vi.fn(() => response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function json(body: unknown, status: number) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }));
}

function fillAndSubmit() {
  for (const [label, value] of Object.entries(FILLED)) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
  }
  fireEvent.click(screen.getByRole("button", { name: "File report" }));
}

function sentBody(fetchMock: ReturnType<typeof stubFetch>) {
  const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
  return JSON.parse(init.body as string);
}

describe("ReportForm", () => {
  it.each(Object.keys(FILLED))("has a labelled %s field", (label) => {
    render(<ReportForm onFiled={() => {}} />);
    expect(screen.getByLabelText(label)).toBeInTheDocument();
  });

  it.each(Object.keys(FILLED))("marks %s as required", (label) => {
    render(<ReportForm onFiled={() => {}} />);
    expect(screen.getByLabelText(label)).toBeRequired();
  });

  it("posts the report to /api/reports", () => {
    const fetchMock = stubFetch(new Promise(() => {}));
    render(<ReportForm onFiled={() => {}} />);
    fillAndSubmit();
    expect(fetchMock).toHaveBeenCalledWith("/api/reports", expect.objectContaining({ method: "POST" }));
  });

  it("sends readings as numbers", () => {
    const fetchMock = stubFetch(new Promise(() => {}));
    render(<ReportForm onFiled={() => {}} />);
    fillAndSubmit();
    expect(sentBody(fetchMock).wind_knots).toBe(12.5);
  });

  it("sends all six fields", () => {
    const fetchMock = stubFetch(new Promise(() => {}));
    render(<ReportForm onFiled={() => {}} />);
    fillAndSubmit();
    expect(sentBody(fetchMock)).toEqual({
      name: "Ada Lovelace",
      station: "Pad 39A",
      wind_knots: 12.5,
      temp_c: 18,
      fuel_pct: 99,
      note: "All readings nominal.",
    });
  });

  it("sends the text fields as typed", () => {
    const fetchMock = stubFetch(new Promise(() => {}));
    render(<ReportForm onFiled={() => {}} />);
    fillAndSubmit();
    expect(sentBody(fetchMock).station).toBe("Pad 39A");
  });

  it("disables the button while the report is being filed", () => {
    stubFetch(new Promise(() => {}));
    render(<ReportForm onFiled={() => {}} />);
    fillAndSubmit();
    expect(screen.getByRole("button", { name: "Filing..." })).toBeDisabled();
  });

  it("hands the filed report to onFiled", async () => {
    stubFetch(json({ id: 7, status: "pending_approval" }, 201));
    const onFiled = vi.fn();
    render(<ReportForm onFiled={onFiled} />);
    fillAndSubmit();
    await screen.findByRole("button", { name: "File report" });
    expect(onFiled).toHaveBeenCalledWith({ id: 7, status: "pending_approval" });
  });

  it("clears the form after a report is filed", async () => {
    stubFetch(json({ id: 7 }, 201));
    render(<ReportForm onFiled={() => {}} />);
    fillAndSubmit();
    await screen.findByRole("button", { name: "File report" });
    expect(screen.getByLabelText("Note")).toHaveValue("");
  });

  it("shows the server's message next to the bad field", async () => {
    stubFetch(json({ errors: [{ field: "fuel_pct", message: "Input should be a valid number" }] }, 422));
    render(<ReportForm onFiled={() => {}} />);
    fillAndSubmit();
    expect(await screen.findByText("Input should be a valid number")).toHaveAttribute("id", "fuel_pct-error");
  });

  it("links the error message to its field for screen readers", async () => {
    stubFetch(json({ errors: [{ field: "fuel_pct", message: "Input should be a valid number" }] }, 422));
    render(<ReportForm onFiled={() => {}} />);
    fillAndSubmit();
    await screen.findByText("Input should be a valid number");
    expect(screen.getByLabelText("Fuel (%)")).toHaveAccessibleDescription("Input should be a valid number");
  });

  it("keeps what was typed when the server rejects the report", async () => {
    stubFetch(json({ errors: [{ field: "note", message: "Too long" }] }, 422));
    render(<ReportForm onFiled={() => {}} />);
    fillAndSubmit();
    await screen.findByText("Too long");
    expect(screen.getByLabelText("Station")).toHaveValue("Pad 39A");
  });

  it("says so when the API cannot be reached", async () => {
    stubFetch(Promise.reject(new TypeError("Failed to fetch")));
    render(<ReportForm onFiled={() => {}} />);
    fillAndSubmit();
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not reach the API");
  });

  it("does not call onFiled when the report is rejected", async () => {
    stubFetch(json({ errors: [{ field: "note", message: "Too long" }] }, 422));
    const onFiled = vi.fn();
    render(<ReportForm onFiled={onFiled} />);
    fillAndSubmit();
    await screen.findByText("Too long");
    expect(onFiled).not.toHaveBeenCalled();
  });
});
