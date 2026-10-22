"""Tests for `lang_tools.lexicon.ingestion.dedup`."""

import pytest

from lang_tools.lexicon.ingestion.dedup import deduplicate
from lang_tools.lexicon.ingestion.dedup import merge_lemmas
from lang_tools.lexicon.lemma import Lemma


def _make(text: str = "amor", **extra: object) -> Lemma:
    return Lemma(
        text=text,
        language="pt",
        part_of_speech="noun",
        **extra,  # type: ignore[arg-type]
    )


def test_merge_lemmas_unions_topics() -> None:
    a = _make(topics=["emotions"])
    b = _make(topics=["relationships"])
    merged = merge_lemmas(a, b)
    assert merged.topics == ["emotions", "relationships"]


def test_merge_lemmas_unions_sources() -> None:
    a = _make(sources=["csv"])
    b = _make(sources=["wiktionary"])
    merged = merge_lemmas(a, b)
    assert merged.sources == ["csv", "wiktionary"]


def test_merge_lemmas_refuses_an_accent_variant() -> None:
    # Identity keeps accents: "acao" and "ação" are two lemmas, never merged.
    with pytest.raises(ValueError, match="different IDs"):
        merge_lemmas(_make(text="acao"), _make(text="ação"))


def test_deduplicate_collapses_duplicates() -> None:
    lemmas = [
        _make(topics=["emotions"]),
        _make(topics=["relationships"]),
        Lemma(text="paz", language="pt", part_of_speech="noun"),
    ]
    deduped = deduplicate(lemmas)
    assert len(deduped) == 2
