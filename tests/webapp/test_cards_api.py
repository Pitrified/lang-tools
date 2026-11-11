"""Tests for the public drill-card read API."""

from typing import TYPE_CHECKING

from lang_tools.lexicon.lemma_store import get_lemmas_filtered

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


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

    def test_excluded_classes_and_the_empty_value(self, client: TestClient) -> None:
        """A listed class is left out; an empty value turns the exclusion off."""
        params = {"language": "pt", "part_of_speech": "noun", "limit": 5}
        left_out = client.get(
            "/api/v1/cards", params={**params, "exclude_part_of_speech": "noun"}
        )
        assert left_out.status_code == 200
        assert left_out.json() == []
        kept = client.get(
            "/api/v1/cards", params={**params, "exclude_part_of_speech": ""}
        )
        assert kept.status_code == 200
        assert kept.json()
        assert all(c["lemma"]["part_of_speech"] == "noun" for c in kept.json())

    def test_forms_only_when_asked(self, client: TestClient) -> None:
        """The seed's inflected forms come back only with ``include_forms``."""
        params = {"language": "pt", "limit": 500, "order": "frequency"}
        default = client.get("/api/v1/cards", params=params).json()
        assert default
        assert all(card["form_note"] is None for card in default)
        every = client.get(
            "/api/v1/cards", params={**params, "include_forms": "true"}
        ).json()
        assert any(card["form_note"] for card in every)

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

    def test_sense_cards(self, client: TestClient) -> None:
        """Every sense comes back as a card, the best one first."""
        known = get_lemmas_filtered(language="pt")[0]
        best = client.get(f"/api/v1/cards/{known.id}").json()
        senses = client.get(f"/api/v1/cards/{known.id}/senses").json()
        assert senses
        assert senses[0]["concept_id"] == best["concept_id"]

    def test_read_missing_card(self, client: TestClient) -> None:
        """An unknown id returns 404."""
        response = client.get("/api/v1/cards/does-not-exist")
        assert response.status_code == 404


class TestKnownLanguages:
    """Look-alike parameters on the card endpoints."""

    def test_known_languages_are_accepted(self, client: TestClient) -> None:
        """The card endpoints take repeated known_languages and a lookalike filter."""
        known = get_lemmas_filtered(language="pt")[0]
        response = client.get(
            f"/api/v1/cards/{known.id}",
            params=[("known_languages", "en"), ("known_languages", "it")],
        )
        assert response.status_code == 200
        assert response.json()["lookalikes"] == []
        response = client.get(
            "/api/v1/cards",
            params=[
                ("language", "pt"),
                ("known_languages", "en"),
                ("lookalike", "none"),
                ("limit", "3"),
            ],
        )
        assert response.status_code == 200
        assert len(response.json()) == 3

    def test_bad_lookalike_filter_is_rejected(self, client: TestClient) -> None:
        """Only trap / cognate / none filter."""
        response = client.get("/api/v1/cards", params={"lookalike": "maybe"})
        assert response.status_code == 422
