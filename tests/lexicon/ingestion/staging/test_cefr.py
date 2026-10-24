"""Tests for the CEFR staging adapter (`ingestion.staging.cefr`)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pyarrow.parquet as pq
import pytest

from lang_tools.lexicon.ingestion.staging.cefr import MissingCefrColumnError
from lang_tools.lexicon.ingestion.staging.cefr import UndownloadableCefrSourceError
from lang_tools.lexicon.ingestion.staging.cefr import UnknownCefrSourceError
from lang_tools.lexicon.ingestion.staging.cefr import download_cefr_source
from lang_tools.lexicon.ingestion.staging.cefr import parse_cefr_rows
from lang_tools.lexicon.ingestion.staging.cefr import stage_cefr_list

if TYPE_CHECKING:
    from pathlib import Path


def test_parse_uppercases_level_and_drops_empty_words() -> None:
    rows = [
        {"word": "house", "level": "a1"},
        {"word": "  ", "level": "b2"},  # blank word -> dropped
        {"word": "ubiquitous", "level": "c1"},
    ]
    cleaned = parse_cefr_rows(rows)
    assert cleaned == [
        {"word": "house", "level": "A1"},
        {"word": "ubiquitous", "level": "C1"},
    ]


def test_parse_strips_curly_quotes_from_level() -> None:
    # Kelly stores levels as `“A1”` (curly quotes).
    rows = [{"word": "the", "level": "“A1”"}, {"word": "be", "level": " 'b2' "}]
    cleaned = parse_cefr_rows(rows)
    assert cleaned == [{"word": "the", "level": "A1"}, {"word": "be", "level": "B2"}]


def test_parse_custom_columns() -> None:
    rows = [{"headword": "casa", "cefr": "a1"}]
    cleaned = parse_cefr_rows(rows, word_col="headword", level_col="cefr")
    assert cleaned == [{"word": "casa", "level": "A1"}]


def test_parse_missing_column_raises() -> None:
    with pytest.raises(MissingCefrColumnError):
        parse_cefr_rows([{"word": "house"}])  # no level column


def test_download_source_rejects_unknown_and_undownloadable(tmp_path: Path) -> None:
    # Both guards run before any network call.
    with pytest.raises(UnknownCefrSourceError):
        download_cefr_source("nope", data_fol=tmp_path)
    with pytest.raises(UndownloadableCefrSourceError):
        download_cefr_source("oxford-en", data_fol=tmp_path)  # PDF, guidance-only


def test_stage_reads_csv_and_writes_parquet(tmp_path: Path) -> None:
    source = tmp_path / "graded_en.csv"
    source.write_text("word,level\nhouse,a1\nrare,c2\n", encoding="utf-8")
    staged = stage_cefr_list(source, language="en", data_fol=tmp_path)
    assert staged.name == "cefr:en"
    assert staged.row_count == 2
    out = tmp_path / staged.path
    table = pq.read_table(out)
    assert table.column("level").to_pylist() == ["A1", "C2"]
