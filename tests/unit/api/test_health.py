"""Unit tests for the health endpoints (SDD 23.1)."""

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app

pytestmark = pytest.mark.unit


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_sdd_23_1_healthz_returns_ok(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_sdd_23_1_readyz_not_configured_returns_503(client: TestClient) -> None:
    response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json() == {"error": {"code": "NOT_CONFIGURED", "message": "not configured"}}
