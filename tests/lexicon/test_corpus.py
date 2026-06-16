"""Tests for the inspect / edit tooling (`lang_tools.lexicon.corpus`)."""

import json
from pathlib import Path

import pytest

from lang_tools.lexicon.codec import MalformedRecordError
from lang_tools.lexicon.codec import _dump_table
from lang_tools.lexicon.codec import _load_table
from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.corpus import export_table
from lang_tools.lexicon.corpus import import_table
from lang_tools.lexicon.corpus import inspect_table

C_ID = "c__library-building__0011aabbccdd"


def _seed_concepts(data_fol: Path) -> None:
    _dump_table(
        "concepts",
        [Concept(id=C_ID, definitions={"en": "a place for books"})],
        data_fol=data_fol,
    )


def test_export_edit_import_round_trip(tmp_path: Path) -> None:
    _seed_concepts(tmp_path)
    jsonl = tmp_path / "concepts.jsonl"
    assert export_table("concepts", jsonl, data_fol=tmp_path) == 1

    # Hand-edit the transient JSONL: change a definition.
    lines = [ln for ln in jsonl.read_text().splitlines() if ln.strip()]
    [row] = [json.loads(ln) for ln in lines]
    row["definitions"]["en"] = "a building that lends books"
    jsonl.write_text(json.dumps(row) + "\n")

    assert import_table("concepts", jsonl, data_fol=tmp_path) == 1
    [loaded] = _load_table("concepts", data_fol=tmp_path)
    assert loaded.definitions["en"] == "a building that lends books"


def test_import_rejects_malformed_row_before_writing(tmp_path: Path) -> None:
    _seed_concepts(tmp_path)
    jsonl = tmp_path / "concepts.jsonl"
    export_table("concepts", jsonl, data_fol=tmp_path)
    # Corrupt the id so model validation fails.
    jsonl.write_text(json.dumps({"id": "bad-id", "definitions": {}}) + "\n")
    with pytest.raises(MalformedRecordError):
        import_table("concepts", jsonl, data_fol=tmp_path)


def test_inspect_table_reads_parquet(tmp_path: Path) -> None:
    _seed_concepts(tmp_path)
    rows = inspect_table("concepts", data_fol=tmp_path)
    assert len(rows) == 1
    assert rows[0]["id"] == C_ID


def test_inspect_table_where_and_limit(tmp_path: Path) -> None:
    _seed_concepts(tmp_path)
    none = inspect_table(
        "concepts",
        data_fol=tmp_path,
        where=f"id = '{C_ID}xxx'",
    )
    assert none == []
    capped = inspect_table("concepts", data_fol=tmp_path, limit=0)
    assert capped == []
