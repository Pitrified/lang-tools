"""Tests for the public word read API."""

from fastapi.testclient import TestClient

from lang_tools.words.word_store import get_words_filtered


class TestListWords:
    """Tests for GET /api/v1/words."""

    def test_list_all_words(self, client: TestClient) -> None:
        """No filter returns the full pool as JSON."""
        response = client.get("/api/v1/words")
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, list)
        assert len(payload) == len(get_words_filtered())

    def test_filter_by_language(self, client: TestClient) -> None:
        """The language filter narrows the result to one language."""
        response = client.get("/api/v1/words", params={"language": "pt"})
        assert response.status_code == 200
        payload = response.json()
        assert payload
        assert all(word["language"] == "pt" for word in payload)
        assert len(payload) == len(get_words_filtered(language="pt"))

    def test_filter_by_topic(self, client: TestClient) -> None:
        """The topic filter narrows the result to words carrying the topic."""
        response = client.get("/api/v1/words", params={"topic": "basics"})
        assert response.status_code == 200
        payload = response.json()
        assert all("basics" in word["topics"] for word in payload)

    def test_word_payload_shape(self, client: TestClient) -> None:
        """Serialized words include computed fields used downstream."""
        response = client.get("/api/v1/words", params={"language": "pt"})
        word = response.json()[0]
        for key in ("id", "text", "language", "has_accent", "length"):
            assert key in word


class TestReadWord:
    """Tests for GET /api/v1/words/{word_id}."""

    def test_read_existing_word(self, client: TestClient) -> None:
        """A known id resolves to its word."""
        known = get_words_filtered(language="pt")[0]
        response = client.get(f"/api/v1/words/{known.id}")
        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == known.id
        assert payload["text"] == known.text

    def test_read_missing_word(self, client: TestClient) -> None:
        """An unknown id returns 404."""
        response = client.get("/api/v1/words/does-not-exist")
        assert response.status_code == 404
        assert "does-not-exist" in response.json()["detail"]
