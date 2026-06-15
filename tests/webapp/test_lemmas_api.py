"""Tests for the public lemma read API."""

from fastapi.testclient import TestClient

from lang_tools.lexicon.lemma_store import get_lemmas_filtered


class TestListLemmas:
    """Tests for GET /api/v1/lemmas."""

    def test_list_all_lemmas(self, client: TestClient) -> None:
        """No filter returns the full pool as JSON."""
        response = client.get("/api/v1/lemmas")
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, list)
        assert len(payload) == len(get_lemmas_filtered())

    def test_filter_by_language(self, client: TestClient) -> None:
        """The language filter narrows the result to one language."""
        response = client.get("/api/v1/lemmas", params={"language": "pt"})
        assert response.status_code == 200
        payload = response.json()
        assert payload
        assert all(lemma["language"] == "pt" for lemma in payload)
        assert len(payload) == len(get_lemmas_filtered(language="pt"))

    def test_filter_by_topic(self, client: TestClient) -> None:
        """The topic filter narrows the result to lemmas carrying the topic."""
        response = client.get("/api/v1/lemmas", params={"topic": "basics"})
        assert response.status_code == 200
        payload = response.json()
        assert all("basics" in lemma["topics"] for lemma in payload)

    def test_lemma_payload_shape(self, client: TestClient) -> None:
        """Serialized lemmas include computed fields used downstream."""
        response = client.get("/api/v1/lemmas", params={"language": "pt"})
        lemma = response.json()[0]
        for key in ("id", "text", "language", "has_accent", "length"):
            assert key in lemma


class TestReadLemma:
    """Tests for GET /api/v1/lemmas/{lemma_id}."""

    def test_read_existing_lemma(self, client: TestClient) -> None:
        """A known id resolves to its lemma."""
        known = get_lemmas_filtered(language="pt")[0]
        response = client.get(f"/api/v1/lemmas/{known.id}")
        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == known.id
        assert payload["text"] == known.text

    def test_read_missing_lemma(self, client: TestClient) -> None:
        """An unknown id returns 404."""
        response = client.get("/api/v1/lemmas/does-not-exist")
        assert response.status_code == 404
        assert "does-not-exist" in response.json()["detail"]
