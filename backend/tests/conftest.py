import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.fakes import pipeline_client


@pytest.fixture(autouse=True)
def no_api_key(monkeypatch):
    """Every test runs as if no Anthropic API key exists."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


@pytest.fixture
def db_path(tmp_path):
    """A fresh SQLite file per test, so tests never touch the real database."""
    return tmp_path / "reports.db"


@pytest.fixture
def client(db_path):
    return TestClient(create_app(llm=pipeline_client(runs=20), db_path=db_path))


@pytest.fixture
def report():
    return {
        "name": "Ada Lovelace",
        "station": "Pad 39A",
        "wind_knots": 12.5,
        "temp_c": 18.0,
        "fuel_pct": 99.0,
        "note": "All readings nominal.",
    }
