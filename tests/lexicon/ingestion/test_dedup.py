"""Tests for `lang_tools.lexicon.ingestion.dedup`."""

from lang_tools.lexicon.ingestion.dedup import deduplicate
from lang_tools.lexicon.ingestion.dedup import merge_lemmas
from lang_tools.lexicon.lemma import Lemma


def _make(text: str = "amor", **extra: object) -> Lemma:
    return Lemma(
        text=text,
        language="pt",
        part_of_speech="noun",
        frequency="medium",
        **extra,  # type: ignore[arg-type]
    )


def test_merge_lemmas_unions_translations() -> None:
    a = _make(translations={"en": "love"})
    b = _make(translations={"fr": "amour"})
    merged = merge_lemmas(a, b)
    assert merged.translations == {"en": "love", "fr": "amour"}


def test_merge_lemmas_prefers_accented_text() -> None:
    a = _make(text="acao")
    b = _make(text="ação")
    merged = merge_lemmas(a, b)
    assert merged.text == "ação"


def test_deduplicate_collapses_duplicates() -> None:
    lemmas = [
        _make(translations={"en": "love"}),
        _make(translations={"fr": "amour"}),
        Lemma(text="paz", language="pt", part_of_speech="noun", frequency="medium"),
    ]
    deduped = deduplicate(lemmas)
    assert len(deduped) == 2
