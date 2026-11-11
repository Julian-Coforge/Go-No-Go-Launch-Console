"""Filing and listing reports through the API. Bad input gets a 422 with an
error that names the field, and is never saved."""


def test_filing_a_report_returns_201(client, report):
    assert client.post("/reports", json=report).status_code == 201


def test_filed_report_gets_an_id(client, report):
    assert client.post("/reports", json=report).json()["id"] == 1


def test_filed_report_echoes_its_fields(client, report):
    assert client.post("/reports", json=report).json()["station"] == "Pad 39A"


def test_filed_report_has_a_created_at_time(client, report):
    assert client.post("/reports", json=report).json()["created_at"]


def test_bad_reading_is_rejected_with_422(client, report):
    report["fuel_pct"] = "full"
    assert client.post("/reports", json=report).status_code == 422


def test_rejection_names_the_bad_field(client, report):
    report["fuel_pct"] = "full"
    errors = client.post("/reports", json=report).json()["errors"]
    assert [error["field"] for error in errors] == ["fuel_pct"]


def test_rejection_gives_a_readable_message(client, report):
    report["name"] = "   "
    errors = client.post("/reports", json=report).json()["errors"]
    assert errors[0]["message"]


def test_missing_field_is_rejected_with_422(client, report):
    del report["note"]
    assert client.post("/reports", json=report).status_code == 422


def test_rejected_report_is_not_saved(client, report):
    report["wind_knots"] = "calm"
    client.post("/reports", json=report)
    assert client.get("/reports").json() == []


def test_list_is_empty_before_any_report(client):
    assert client.get("/reports").json() == []


def test_list_includes_a_filed_report(client, report):
    client.post("/reports", json=report)
    assert len(client.get("/reports").json()) == 1


def test_list_shows_newest_first(client, report):
    client.post("/reports", json=report)
    client.post("/reports", json={**report, "station": "Pad 40"})
    assert client.get("/reports").json()[0]["station"] == "Pad 40"


def test_one_report_can_be_fetched_by_id(client, report):
    report_id = client.post("/reports", json=report).json()["id"]
    assert client.get(f"/reports/{report_id}").json()["name"] == "Ada Lovelace"


def test_unknown_report_id_returns_404(client):
    assert client.get("/reports/999").status_code == 404
