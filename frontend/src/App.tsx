import { useEffect, useState } from "react";

type ApiStatus = "checking" | "online" | "offline";

const STATUS_TEXT: Record<ApiStatus, string> = {
  checking: "Checking API...",
  online: "API online",
  offline: "API offline",
};

export default function App() {
  const [status, setStatus] = useState<ApiStatus>("checking");

  useEffect(() => {
    let active = true;
    fetch("/api/health")
      .then((response) => response.json())
      .then((body) => active && setStatus(body.status === "ok" ? "online" : "offline"))
      .catch(() => active && setStatus("offline"));
    return () => {
      active = false;
    };
  }, []);

  return (
    <main>
      <h1>Mission Control</h1>
      <p role="status">{STATUS_TEXT[status]}</p>
    </main>
  );
}
