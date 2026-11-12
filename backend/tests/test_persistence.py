"""Reports are saved to SQLite and are still there after a restart."""

import sqlite3

from fastapi.testclient import TestClient

from app.main import create_app
from tests.fakes import pipeline_client


def start_app(db_path):
    return TestClient(create_app(llm=pipeline_client(runs=5), db_path=db_path))


def test_report_survives_a_restart(db_path, report):
    start_app(db_path).post("/reports", json=report)
    restarted = start_app(db_path)
    assert restarted.get("/reports").json()[0]["note"] == "All readings nominal."


def test_ids_keep_counting_after_a_restart(db_path, report):
    start_app(db_path).post("/reports", json=report)
    restarted = start_app(db_path)
    assert restarted.post("/reports", json=report).json()["id"] == 2


def test_database_file_is_created_on_start(db_path):
    start_app(db_path)
    assert db_path.exists()


def test_pipeline_results_survive_a_restart(db_path, report):
    report_id = start_app(db_path).post("/reports", json=report).json()["id"]
    restarted = start_app(db_path)
    assert restarted.get(f"/reports/{report_id}").json()["status"] == "pending_approval"


def test_trace_survives_a_restart(db_path, report):
    report_id = start_app(db_path).post("/reports", json=report).json()["id"]
    restarted = start_app(db_path)
    assert len(restarted.get(f"/reports/{report_id}").json()["trace"]) == 8


def make_pre_pipeline_db(db_path):
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE reports (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,"
            " station TEXT NOT NULL, wind_knots REAL NOT NULL, temp_c REAL NOT NULL,"
            " fuel_pct REAL NOT NULL, note TEXT NOT NULL, created_at TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO reports (name, station, wind_knots, temp_c, fuel_pct, note, created_at)"
            " VALUES ('Old', 'Pad 1', 10, 10, 99, 'old', '2026-11-11T00:00:00+00:00')"
        )


def test_database_from_before_the_pipeline_still_starts(db_path):
    make_pre_pipeline_db(db_path)
    assert start_app(db_path).get("/reports").json() == []


def test_reports_from_before_the_pipeline_are_kept_aside(db_path):
    make_pre_pipeline_db(db_path)
    start_app(db_path)
    with sqlite3.connect(db_path) as conn:
        kept = conn.execute("SELECT COUNT(*) FROM reports_pre_pipeline").fetchone()[0]
    assert kept == 1
