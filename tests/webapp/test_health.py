"""Tests for the built-in health endpoint exposed by the read API."""

from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    """The fastapi-tools health endpoint responds successfully."""
    response = client.get("/health")
    assert response.status_code == 200
