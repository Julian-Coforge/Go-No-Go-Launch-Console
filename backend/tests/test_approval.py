"""Only a person can approve a report, through POST /reports/{id}/approve.
It works once, from pending_approval or needs_review, and records who
approved it and when. The pipeline and every other route leave it alone."""

import sqlite3

from fastapi.testclient import TestClient

from app.main import create_app
from tests.fakes import FLAGGED, pipeline_client

APPROVER = {"approver_name": "Gene Kranz"}


def start_app(db_path, **script):
    return TestClient(create_app(llm=pipeline_client(runs=5, **script), db_path=db_path))


def file_report(client, report):
    return client.post("/reports", json=report).json()["id"]


def approve(client, report_id, body=APPROVER):
    return client.post(f"/reports/{report_id}/approve", json=body)


def test_new_report_has_no_approver(client, report):
    assert client.post("/reports", json=report).json()["approved_by"] is None


def test_approve_returns_200(client, report):
    assert approve(client, file_report(client, report)).status_code == 200


def test_approve_sets_status_to_approved(client, report):
    assert approve(client, file_report(client, report)).json()["status"] == "approved"


def test_approve_records_who_approved(client, report):
    assert approve(client, file_report(client, report)).json()["approved_by"] == "Gene Kranz"


def test_approve_records_when(client, report):
    assert approve(client, file_report(client, report)).json()["approved_at"]


def test_approver_name_is_trimmed(client, report):
    body = {"approver_name": "  Gene Kranz  "}
    assert approve(client, file_report(client, report), body).json()["approved_by"] == "Gene Kranz"


def test_approval_is_saved(client, report):
    report_id = file_report(client, report)
    approve(client, report_id)
    assert client.get(f"/reports/{report_id}").json()["status"] == "approved"


def test_report_needing_review_can_be_approved_after_review(db_path, report):
    client = start_app(db_path, injection=FLAGGED)
    report_id = file_report(client, report)
    assert approve(client, report_id).json()["status"] == "approved"


def test_second_approval_returns_409(client, report):
    report_id = file_report(client, report)
    approve(client, report_id)
    assert approve(client, report_id).status_code == 409


def test_second_approval_keeps_the_first_approver(client, report):
    report_id = file_report(client, report)
    approve(client, report_id)
    approve(client, report_id, {"approver_name": "Someone Else"})
    assert client.get(f"/reports/{report_id}").json()["approved_by"] == "Gene Kranz"


def test_unknown_report_returns_404_naming_the_report(client):
    # Checks the message too: a missing route would also give a plain 404.
    assert approve(client, 999).json()["detail"] == "Report 999 not found"


def test_missing_name_returns_422(client, report):
    assert approve(client, file_report(client, report), {}).status_code == 422


def test_blank_name_is_rejected_with_its_field(client, report):
    errors = approve(client, file_report(client, report), {"approver_name": "  "}).json()["errors"]
    assert [error["field"] for error in errors] == ["approver_name"]


def test_approval_survives_a_restart(db_path, report):
    first = start_app(db_path)
    report_id = file_report(first, report)
    approve(first, report_id)
    assert start_app(db_path).get(f"/reports/{report_id}").json()["approved_by"] == "Gene Kranz"


def test_filing_cannot_set_approved(client, report):
    report.update(status="approved", approved_by="Mallory")
    assert client.post("/reports", json=report).json()["status"] == "pending_approval"


def test_only_filing_and_approving_change_data(client):
    writes = {
        route.path
        for route in client.app.routes
        if getattr(route, "methods", set()) & {"POST", "PUT", "PATCH", "DELETE"}
    }
    assert writes == {"/reports", "/reports/{report_id}/approve"}


def make_pipeline_era_db(db_path):
    """The table as it was before approval columns existed."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE reports (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,"
            " station TEXT NOT NULL, wind_knots REAL NOT NULL, temp_c REAL NOT NULL,"
            " fuel_pct REAL NOT NULL, note TEXT NOT NULL, created_at TEXT NOT NULL,"
            " status TEXT NOT NULL, result_json TEXT NOT NULL)"
        )


def test_database_from_before_approval_can_approve(db_path, report):
    make_pipeline_era_db(db_path)
    client = start_app(db_path)
    assert approve(client, file_report(client, report)).status_code == 200
