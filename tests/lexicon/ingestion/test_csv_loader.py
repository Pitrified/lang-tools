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


def test_load_csv_with_translations() -> None:
    content = "text,language,translation_en\namor,pt,love\n"
    lemmas = list(load_csv(StringIO(content)))
    assert lemmas[0].translations == {"en": "love"}


def test_load_csv_missing_required_columns() -> None:
    content = "word,lang\namor,pt\n"
    with pytest.raises(CSVColumnsMissingError):
        list(load_csv(StringIO(content)))
