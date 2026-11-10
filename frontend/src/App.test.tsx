import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import App from "./App";

function stubHealth(response: Promise<Response>) {
  vi.stubGlobal("fetch", vi.fn(() => response));
}

describe("App", () => {
  it("shows the Mission Control title", () => {
    stubHealth(new Promise(() => {}));
    render(<App />);
    expect(screen.getByRole("heading", { name: "Mission Control" })).toBeInTheDocument();
  });

  it("shows the API as online when /api/health answers ok", async () => {
    stubHealth(Promise.resolve(new Response(JSON.stringify({ status: "ok" }))));
    render(<App />);
    expect(await screen.findByText("API online")).toBeInTheDocument();
  });

  it("shows the API as offline when /api/health cannot be reached", async () => {
    stubHealth(Promise.reject(new TypeError("Failed to fetch")));
    render(<App />);
    expect(await screen.findByText("API offline")).toBeInTheDocument();
  });

  it("asks the back end through the /api proxy", () => {
    stubHealth(new Promise(() => {}));
    render(<App />);
    expect(fetch).toHaveBeenCalledWith("/api/health");
  });
});
