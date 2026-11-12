import { type FormEvent, useState } from "react";

type FieldName = "name" | "station" | "wind_knots" | "temp_c" | "fuel_pct" | "note";

type Field = {
  name: FieldName;
  label: string;
  kind: "text" | "number" | "note";
};

const FIELDS: Field[] = [
  { name: "name", label: "Name", kind: "text" },
  { name: "station", label: "Station", kind: "text" },
  { name: "wind_knots", label: "Wind (knots)", kind: "number" },
  { name: "temp_c", label: "Temperature (°C)", kind: "number" },
  { name: "fuel_pct", label: "Fuel (%)", kind: "number" },
  { name: "note", label: "Note", kind: "note" },
];

const EMPTY: Record<FieldName, string> = {
  name: "",
  station: "",
  wind_knots: "",
  temp_c: "",
  fuel_pct: "",
  note: "",
};

type ServerError = { field: string; message: string };

// Readings go to the API as numbers. An empty reading is sent as null so the
// server rejects it with a message that names the field.
function toPayload(values: Record<FieldName, string>) {
  const payload: Record<string, string | number | null> = {};
  for (const field of FIELDS) {
    const value = values[field.name];
    payload[field.name] = field.kind === "number" ? (value === "" ? null : Number(value)) : value;
  }
  return payload;
}

export default function ReportForm({ onFiled }: { onFiled: (report: unknown) => void }) {
  const [values, setValues] = useState(EMPTY);
  const [errors, setErrors] = useState<Partial<Record<string, string>>>({});
  const [alert, setAlert] = useState<string | null>(null);
  const [filing, setFiling] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setFiling(true);
    setErrors({});
    setAlert(null);
    try {
      const response = await fetch("/api/reports", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toPayload(values)),
      });
      const body = await response.json();
      if (response.status === 422) {
        const byField: Record<string, string> = {};
        for (const error of body.errors as ServerError[]) byField[error.field] = error.message;
        setErrors(byField);
      } else if (!response.ok) {
        setAlert(`The API returned an error (${response.status})`);
      } else {
        setValues(EMPTY);
        onFiled(body);
      }
    } catch {
      setAlert("Could not reach the API");
    } finally {
      setFiling(false);
    }
  }

  return (
    <form onSubmit={submit} aria-label="File a report">
      {FIELDS.map((field) => {
        const id = `field-${field.name}`;
        const errorId = `${field.name}-error`;
        const error = errors[field.name];
        const common = {
          id,
          name: field.name,
          required: true,
          value: values[field.name],
          "aria-invalid": error ? true : undefined,
          "aria-describedby": error ? errorId : undefined,
          onChange: (event: { target: { value: string } }) =>
            setValues((current) => ({ ...current, [field.name]: event.target.value })),
        };
        return (
          <div className="field" key={field.name}>
            <label htmlFor={id}>{field.label}</label>
            {field.kind === "note" ? (
              <textarea {...common} maxLength={2000} rows={4} />
            ) : field.kind === "number" ? (
              <input {...common} type="number" step="any" />
            ) : (
              <input {...common} type="text" maxLength={100} />
            )}
            {error && (
              <p className="field-error" id={errorId}>
                {error}
              </p>
            )}
          </div>
        );
      })}
      {alert && <p role="alert">{alert}</p>}
      <button type="submit" disabled={filing}>
        {filing ? "Filing..." : "File report"}
      </button>
    </form>
  );
}
