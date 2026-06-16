"""Tests for the public concept / relation read API.

The default store has no concept or relation data yet (Parquet corpus is
produced in phase 5), so these assert the contract shape and the not-found /
empty behaviour rather than populated payloads.
"""

from fastapi.testclient import TestClient


class TestReadConcept:
    """Tests for GET /api/v1/concepts/{concept_id}."""

    def test_missing_concept_returns_404(self, client: TestClient) -> None:
        """An unknown concept id returns 404."""
        response = client.get("/api/v1/concepts/c__nope__000000000000")
        assert response.status_code == 404
        assert "c__nope__000000000000" in response.json()["detail"]


class TestConceptRelations:
    """Tests for GET /api/v1/concepts/{concept_id}/relations."""

    def test_unknown_concept_returns_empty_list(self, client: TestClient) -> None:
        """An unknown concept yields an empty relation list, not a 404."""
        response = client.get("/api/v1/concepts/c__nope__000000000000/relations")
        assert response.status_code == 200
        assert response.json() == []


class TestFalseFriends:
    """Tests for GET /api/v1/lemmas/{lemma_id}/false-friends."""

    def test_unknown_lemma_returns_empty_list(self, client: TestClient) -> None:
        """A lemma with no false friends yields an empty list."""
        response = client.get("/api/v1/lemmas/does-not-exist/false-friends")
        assert response.status_code == 200
        assert response.json() == []
