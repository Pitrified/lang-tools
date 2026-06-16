"""Tests for `lang_tools.lexicon.ingestion.dedup`."""

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


def test_merge_lemmas_prefers_accented_text() -> None:
    a = _make(text="acao")
    b = _make(text="ação")
    merged = merge_lemmas(a, b)
    assert merged.text == "ação"


def test_deduplicate_collapses_duplicates() -> None:
    lemmas = [
        _make(topics=["emotions"]),
        _make(topics=["relationships"]),
        Lemma(text="paz", language="pt", part_of_speech="noun"),
    ]
    deduped = deduplicate(lemmas)
    assert len(deduped) == 2
