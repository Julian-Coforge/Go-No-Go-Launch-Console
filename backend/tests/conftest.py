import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(autouse=True)
def no_api_key(monkeypatch):
    """Every test runs as if no Anthropic API key exists."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


@pytest.fixture
def client():
    return TestClient(create_app())
