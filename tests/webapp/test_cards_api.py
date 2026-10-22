"""Tests for the public drill-card read API."""

from fastapi.testclient import TestClient

from lang_tools.lexicon.lemma_store import get_lemmas_filtered


class TestListCards:
    """Tests for GET /api/v1/cards."""

    def test_filters_and_limit(self, client: TestClient) -> None:
        """The query string is a CardQuery; the page honours its filters."""
        response = client.get(
            "/api/v1/cards",
            params={"language": "pt", "single_word": True, "limit": 5, "seed": 1},
        )
        assert response.status_code == 200
        cards = response.json()
        assert 0 < len(cards) <= 5
        for card in cards:
            assert card["lemma"]["language"] == "pt"
            assert card["lemma"]["text"].isalpha()
            assert set(card["translations"]) == {"en"}

    def test_repeated_translation_languages(self, client: TestClient) -> None:
        """List fields repeat the key in the query string."""
        response = client.get(
            "/api/v1/cards",
            params=[
                ("language", "pt"),
                ("translation_languages", "en"),
                ("translation_languages", "it"),
                ("limit", "3"),
            ],
        )
        assert response.status_code == 200
        assert all(
            set(card["translations"]) == {"en", "it"} for card in response.json()
        )

    def test_seeded_sample_is_stable(self, client: TestClient) -> None:
        """The same seed returns the same cards."""
        params = {"language": "en", "limit": 5, "seed": 3}
        first = client.get("/api/v1/cards", params=params).json()
        second = client.get("/api/v1/cards", params=params).json()
        assert [c["lemma"]["id"] for c in first] == [c["lemma"]["id"] for c in second]

    def test_bad_level_is_rejected(self, client: TestClient) -> None:
        """A value outside the CEFR bands is a validation error."""
        response = client.get("/api/v1/cards", params={"max_cefr": "Z9"})
        assert response.status_code == 422


class TestReadCard:
    """Tests for GET /api/v1/cards/{lemma_id}."""

    def test_read_existing_card(self, client: TestClient) -> None:
        """A known id resolves to its card, with the requested gloss language."""
        known = get_lemmas_filtered(language="pt")[0]
        response = client.get(
            f"/api/v1/cards/{known.id}",
            params={"gloss_language": "pt"},
        )
        assert response.status_code == 200
        card = response.json()
        assert card["lemma"]["id"] == known.id
        assert "en" in card["translations"]

    def test_read_missing_card(self, client: TestClient) -> None:
        """An unknown id returns 404."""
        response = client.get("/api/v1/cards/does-not-exist")
        assert response.status_code == 404
