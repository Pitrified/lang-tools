"""Tests for `lang_tools.words.ingestion.csv_loader`."""

from io import StringIO

import pytest

from lang_tools.words.ingestion.csv_loader import CSVColumnsMissingError
from lang_tools.words.ingestion.csv_loader import load_csv


def test_load_csv_minimal() -> None:
    content = "text,language\namor,pt\namour,fr\n"
    words = list(load_csv(StringIO(content)))
    assert len(words) == 2
    assert {w.language for w in words} == {"pt", "fr"}
    assert all(w.sources == ["csv"] for w in words)


def test_load_csv_with_translations() -> None:
    content = "text,language,translation_en\namor,pt,love\n"
    words = list(load_csv(StringIO(content)))
    assert words[0].translations == {"en": "love"}


def test_load_csv_missing_required_columns() -> None:
    content = "word,lang\namor,pt\n"
    with pytest.raises(CSVColumnsMissingError):
        list(load_csv(StringIO(content)))
