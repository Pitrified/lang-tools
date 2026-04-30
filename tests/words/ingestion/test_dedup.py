"""Tests for `lang_tools.words.ingestion.dedup`."""

from lang_tools.words.ingestion.dedup import deduplicate
from lang_tools.words.ingestion.dedup import merge_words
from lang_tools.words.word import Word


def _make(text: str = "amor", **extra: object) -> Word:
    return Word(
        text=text,
        language="pt",
        part_of_speech="noun",
        frequency="medium",
        **extra,  # type: ignore[arg-type]
    )


def test_merge_words_unions_translations() -> None:
    a = _make(translations={"en": "love"})
    b = _make(translations={"fr": "amour"})
    merged = merge_words(a, b)
    assert merged.translations == {"en": "love", "fr": "amour"}


def test_merge_words_prefers_accented_text() -> None:
    a = _make(text="acao")
    b = _make(text="ação")
    merged = merge_words(a, b)
    assert merged.text == "ação"


def test_deduplicate_collapses_duplicates() -> None:
    words = [
        _make(translations={"en": "love"}),
        _make(translations={"fr": "amour"}),
        Word(text="paz", language="pt", part_of_speech="noun", frequency="medium"),
    ]
    deduped = deduplicate(words)
    assert len(deduped) == 2
