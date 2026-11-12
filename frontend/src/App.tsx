import { useEffect, useState } from "react";

import ReportForm from "./ReportForm";
import ReportList from "./ReportList";
import type { Report } from "./types";

type ApiStatus = "checking" | "online" | "offline";

const STATUS_TEXT: Record<ApiStatus, string> = {
  checking: "Checking API...",
  online: "API online",
  offline: "API offline",
};

export default function App() {
  const [status, setStatus] = useState<ApiStatus>("checking");
  const [reports, setReports] = useState<Report[]>([]);
  const [loadFailed, setLoadFailed] = useState(false);

  useEffect(() => {
    let active = true;
    fetch("/api/health")
      .then((response) => response.json())
      .then((body) => active && setStatus(body.status === "ok" ? "online" : "offline"))
      .catch(() => active && setStatus("offline"));
    fetch("/api/reports")
      .then((response) => {
        if (!response.ok) throw new Error(`GET /reports returned ${response.status}`);
        return response.json();
      })
      // A report filed while the list loads is kept at the top.
      .then((loaded: Report[]) =>
        active &&
        setReports((current) => [
          ...current,
          ...loaded.filter((report) => !current.some((filed) => filed.id === report.id)),
        ]),
      )
      .catch(() => active && setLoadFailed(true));
    return () => {
      active = false;
    };
  }, []);

  return (
    <main>
      <h1>Mission Control</h1>
      <p role="status">{STATUS_TEXT[status]}</p>

      <section aria-labelledby="file-heading">
        <h2 id="file-heading">File a report</h2>
        <ReportForm onFiled={(report) => setReports((current) => [report as Report, ...current])} />
      </section>

      <section aria-labelledby="reports-heading">
        <h2 id="reports-heading">Reports</h2>
        {loadFailed ? <p>Could not load reports.</p> : <ReportList reports={reports} />}
      </section>
    </main>
  );
}
