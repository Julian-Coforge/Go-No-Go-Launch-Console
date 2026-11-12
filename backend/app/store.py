"""SQLite storage for filed reports and their pipeline results. The
database is a single file, so reports are still there after the app
restarts."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

from app.pipeline import PipelineResult, ReportOut
from app.schemas import ReportIn

SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    station TEXT NOT NULL,
    wind_knots REAL NOT NULL,
    temp_c REAL NOT NULL,
    fuel_pct REAL NOT NULL,
    note TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL,
    result_json TEXT NOT NULL
)
"""

COLUMNS = "id, name, station, wind_knots, temp_c, fuel_pct, note, created_at, status, result_json"

# Reports saved before the pipeline existed have no results. They are moved
# to this table (not deleted) so the app can start on an older database.
PRE_PIPELINE_TABLE = "reports_pre_pipeline"


class ReportStore:
    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            self._move_aside_pre_pipeline_table(conn)
            conn.execute(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _move_aside_pre_pipeline_table(conn: sqlite3.Connection) -> None:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(reports)")}
        if columns and "result_json" not in columns:
            conn.execute(f"ALTER TABLE reports RENAME TO {PRE_PIPELINE_TABLE}")

    @staticmethod
    def _to_report(row: sqlite3.Row) -> ReportOut:
        data = dict(row)
        results = json.loads(data.pop("result_json"))
        # The status column is the source of truth, so a later approval
        # only has to update one place.
        results["status"] = data.pop("status")
        return ReportOut(**data, **results)

    def add(self, report: ReportIn, result: PipelineResult) -> ReportOut:
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO reports (name, station, wind_knots, temp_c, fuel_pct, note,"
                " created_at, status, result_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    report.name,
                    report.station,
                    report.wind_knots,
                    report.temp_c,
                    report.fuel_pct,
                    report.note,
                    created_at,
                    result.status,
                    result.model_dump_json(exclude={"status"}),
                ),
            )
            report_id = cursor.lastrowid
        return ReportOut(
            id=report_id, created_at=created_at, **report.model_dump(), **result.model_dump()
        )

    def list_all(self) -> list[ReportOut]:
        with self._connect() as conn:
            rows = conn.execute(f"SELECT {COLUMNS} FROM reports ORDER BY id DESC").fetchall()
        return [self._to_report(row) for row in rows]

    def get(self, report_id: int) -> Optional[ReportOut]:
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT {COLUMNS} FROM reports WHERE id = ?", (report_id,)
            ).fetchone()
        return self._to_report(row) if row else None
