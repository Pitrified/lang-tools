"""Tests for the public lemma read API."""

from typing import TYPE_CHECKING

from lang_tools.lexicon.lemma_store import get_lemmas_filtered

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


class TestListLemmas:
    """Tests for GET /api/v1/lemmas."""

    def test_list_is_paged_with_a_total(self, client: TestClient) -> None:
        """No filter returns the first page, with the pool size in a header."""
        response = client.get("/api/v1/lemmas")
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, list)
        total = len(get_lemmas_filtered())
        assert len(payload) == min(100, total)
        assert response.headers["X-Total-Count"] == str(total)

    def test_pages_do_not_overlap(self, client: TestClient) -> None:
        """Consecutive pages are disjoint and ordered by the folded form."""
        first = client.get("/api/v1/lemmas", params={"limit": 5}).json()
        second = client.get("/api/v1/lemmas", params={"limit": 5, "offset": 5}).json()
        assert not {lem["id"] for lem in first} & {lem["id"] for lem in second}
        assert first[-1]["normalized"] <= second[0]["normalized"]

    def test_prefix_search(self, client: TestClient) -> None:
        """``q`` matches the start of the folded form."""
        known = get_lemmas_filtered(language="pt")[0]
        response = client.get(
            "/api/v1/lemmas",
            params={"language": "pt", "q": known.normalized[:3]},
        )
        assert known.id in {lem["id"] for lem in response.json()}
        assert all(
            lem["normalized"].startswith(known.normalized[:3])
            for lem in response.json()
        )

    def test_page_size_is_capped(self, client: TestClient) -> None:
        """A page larger than the cap is rejected."""
        response = client.get("/api/v1/lemmas", params={"limit": 10_000})
        assert response.status_code == 422

    def test_filter_by_language(self, client: TestClient) -> None:
        """The language filter narrows the result to one language."""
        response = client.get("/api/v1/lemmas", params={"language": "pt"})
        assert response.status_code == 200
        payload = response.json()
        assert payload
        assert all(lemma["language"] == "pt" for lemma in payload)
        expected = len(get_lemmas_filtered(language="pt"))
        assert len(payload) == min(100, expected)

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
