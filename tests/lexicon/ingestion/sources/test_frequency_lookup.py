"""Tests for the token-frequency lookup (`ingestion.sources.frequency`)."""

import pytest

from lang_tools.lexicon.ingestion.sources.frequency import lemma_zipf
from lang_tools.lexicon.lemma import Lemma

pytest.importorskip("wordfreq")


def _lemma(text: str, language: str = "en") -> Lemma:
    return Lemma(text=text, language=language)


def test_a_capitalized_twin_is_not_lent_the_lowercase_frequency() -> None:
    # wordfreq lowercases: without the guard, beryllium "Be" scores like "be".
    scores = lemma_zipf([_lemma("be"), _lemma("Be")])
    assert ("be", "en") in scores
    assert ("Be", "en") not in scores


def test_a_capitalized_lemma_without_a_twin_keeps_its_lookup() -> None:
    assert ("Paris", "en") in lemma_zipf([_lemma("Paris")])
