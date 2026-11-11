"""Reports are saved to SQLite and are still there after a restart."""

from fastapi.testclient import TestClient

from app.llm import FakeClient
from app.main import create_app


def start_app(db_path):
    return TestClient(create_app(llm=FakeClient({}), db_path=db_path))


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
