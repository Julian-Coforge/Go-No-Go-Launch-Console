"""SQLite storage for filed reports. The database is a single file, so
reports are still there after the app restarts."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

from app.schemas import ReportIn, ReportOut

SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    station TEXT NOT NULL,
    wind_knots REAL NOT NULL,
    temp_c REAL NOT NULL,
    fuel_pct REAL NOT NULL,
    note TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""

COLUMNS = "id, name, station, wind_knots, temp_c, fuel_pct, note, created_at"


class ReportStore:
    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def add(self, report: ReportIn) -> ReportOut:
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO reports (name, station, wind_knots, temp_c, fuel_pct, note, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    report.name,
                    report.station,
                    report.wind_knots,
                    report.temp_c,
                    report.fuel_pct,
                    report.note,
                    created_at,
                ),
            )
            report_id = cursor.lastrowid
        return ReportOut(id=report_id, created_at=created_at, **report.model_dump())

    def list_all(self) -> list[ReportOut]:
        with self._connect() as conn:
            rows = conn.execute(f"SELECT {COLUMNS} FROM reports ORDER BY id DESC").fetchall()
        return [ReportOut(**dict(row)) for row in rows]

    def get(self, report_id: int) -> Optional[ReportOut]:
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT {COLUMNS} FROM reports WHERE id = ?", (report_id,)
            ).fetchone()
        return ReportOut(**dict(row)) if row else None
