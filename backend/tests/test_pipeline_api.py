"""Filing a report through the API runs the pipeline and saves its results."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from tests.fakes import FLAGGED, pipeline_client

INJECTION_NOTE = (Path(__file__).parent / "fixtures" / "injection_note.txt").read_text().strip()


def test_filed_report_gets_a_status(client, report):
    assert client.post("/reports", json=report).json()["status"] == "pending_approval"


def test_filed_report_gets_a_verdict(client, report):
    report["wind_knots"] = 30
    assert client.post("/reports", json=report).json()["verdict"] == "no_go"


def test_filed_report_gets_a_brief_by_time(client, report):
    assert client.post("/reports", json=report).json()["brief_by_minutes"] == 30


def test_filed_report_gets_a_briefing(client, report):
    assert client.post("/reports", json=report).json()["briefing"].startswith("GO for launch")


def test_filed_report_gets_a_trace(client, report):
    assert len(client.post("/reports", json=report).json()["trace"]) == 8


def test_filed_report_gets_a_total_cost(client, report):
    assert client.post("/reports", json=report).json()["total_cost_usd"] > 0


def test_saved_report_keeps_its_pipeline_results(client, report):
    report_id = client.post("/reports", json=report).json()["id"]
    assert client.get(f"/reports/{report_id}").json()["classification"]["subsystem"] == "propulsion"


def test_list_shows_each_report_status(client, report):
    client.post("/reports", json=report)
    assert client.get("/reports").json()[0]["status"] == "pending_approval"


def test_injection_note_is_sent_to_review(db_path, report):
    client = TestClient(create_app(llm=pipeline_client(injection=FLAGGED), db_path=db_path))
    report.update(note=INJECTION_NOTE, wind_knots=30)
    assert client.post("/reports", json=report).json()["status"] == "needs_review"


def test_injection_note_does_not_change_the_verdict(db_path, report):
    client = TestClient(create_app(llm=pipeline_client(injection=FLAGGED), db_path=db_path))
    report.update(note=INJECTION_NOTE, wind_knots=30)
    assert client.post("/reports", json=report).json()["verdict"] == "no_go"
