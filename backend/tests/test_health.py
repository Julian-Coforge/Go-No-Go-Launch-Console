def test_health_returns_200(client):
    assert client.get("/health").status_code == 200


def test_health_reports_ok(client):
    assert client.get("/health").json() == {"status": "ok"}
