"""Tests for the Tatoeba staging adapter's pure cores (`ingestion.staging.tatoeba`).

The HTTPS download (`download_tatoeba_sentences`) is network-isolated and not
exercised; only the parser and the lemma->sentence index are tested.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from lang_tools.lexicon.ingestion.staging.tatoeba import UnknownTatoebaLanguageError
from lang_tools.lexicon.ingestion.staging.tatoeba import _tatoeba_iso3
from lang_tools.lexicon.ingestion.staging.tatoeba import build_lemma_sentence_index
from lang_tools.lexicon.ingestion.staging.tatoeba import lemma_forms_by_language
from lang_tools.lexicon.ingestion.staging.tatoeba import parse_tatoeba_tsv


def test_iso3_known_and_unknown() -> None:
    assert _tatoeba_iso3("it") == "ita"
    with pytest.raises(UnknownTatoebaLanguageError):
        _tatoeba_iso3("xx")


def test_parse_tsv_drops_lang_and_skips_malformed() -> None:
    lines = [
        "1\teng\tThe house is big.",
        "2\teng\t",  # empty text -> skipped
        "bad\teng\tno integer id",  # non-int id -> skipped
        "5\teng",  # wrong field count -> skipped
        "4\teng\tI live in a house",
    ]
    rows = list(parse_tatoeba_tsv(lines))
    assert rows == [(1, "The house is big."), (4, "I live in a house")]


def test_index_matches_tokens_not_substrings_and_strips_punctuation() -> None:
    sentences = [
        (1, "The house is big."),
        (2, "I live in a house"),
        (3, "A housewife works hard"),  # must NOT match "house"
    ]
    index = build_lemma_sentence_index(sentences, ["house"])
    assert index == {"house": [1, 2]}


def test_index_matches_multiword_form_contiguously() -> None:
    sentences = [
        (1, "a big house here"),
        (2, "the house is big"),  # tokens present but not contiguous -> no match
    ]
    index = build_lemma_sentence_index(sentences, ["big house"])
    assert index == {"big house": [1]}


def test_index_dedupes_repeated_form_within_a_sentence() -> None:
    index = build_lemma_sentence_index([(1, "house to house, house")], ["house"])
    assert index == {"house": [1]}


def test_index_is_accent_insensitive() -> None:
    index = build_lemma_sentence_index([(1, "Uma casa grande")], ["casá"])
    assert index == {"casá": [1]}


def test_index_respects_the_per_lemma_cap() -> None:
    sentences = [(i, "a house") for i in range(10)]
    index = build_lemma_sentence_index(sentences, ["house"], max_per_lemma=3)
    assert index == {"house": [0, 1, 2]}


@dataclass
class _FakeLemma:
    language: str
    text: str


def test_lemma_forms_by_language_groups() -> None:
    lemmas = [
        _FakeLemma("en", "house"),
        _FakeLemma("en", "water"),
        _FakeLemma("it", "casa"),
    ]
    grouped = lemma_forms_by_language(lemmas)
    assert grouped == {"en": ["house", "water"], "it": ["casa"]}
