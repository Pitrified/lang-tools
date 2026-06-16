"""Tests for `lang_tools.lexicon.ingestion.csv_loader`."""

from io import StringIO

import pytest

from lang_tools.lexicon.ingestion.csv_loader import CSVColumnsMissingError
from lang_tools.lexicon.ingestion.csv_loader import load_csv


def test_load_csv_minimal() -> None:
    content = "text,language\namor,pt\namour,fr\n"
    lemmas = list(load_csv(StringIO(content)))
    assert len(lemmas) == 2
    assert {lemma.language for lemma in lemmas} == {"pt", "fr"}
    assert all(lemma.sources == ["csv"] for lemma in lemmas)


def test_load_csv_parses_topics_and_examples() -> None:
    content = (
        "text,language,part_of_speech,topics,example_sentence,example_translation\n"
        "amor,pt,noun,emotions,Eu sinto amor.,I feel love.\n"
    )
    lemma = next(load_csv(StringIO(content)))
    assert lemma.part_of_speech == "noun"
    assert lemma.topics == ["emotions"]
    assert lemma.examples[0].sentence == "Eu sinto amor."
    assert lemma.examples[0].translation == "I feel love."


def test_load_csv_ignores_legacy_columns() -> None:
    content = "text,language,frequency,translation_en\namor,pt,high,love\n"
    lemma = next(load_csv(StringIO(content)))
    assert lemma.text == "amor"
    assert lemma.model_dump().keys() == {
        "text",
        "language",
        "normalized",
        "part_of_speech",
        "topics",
        "examples",
        "sources",
        "id",
        "has_accent",
        "accented_chars",
        "length",
    }


def test_load_csv_missing_required_columns() -> None:
    content = "word,lang\namor,pt\n"
    with pytest.raises(CSVColumnsMissingError):
        list(load_csv(StringIO(content)))
