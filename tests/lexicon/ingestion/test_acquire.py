"""Tests for the acquire stage's pure helpers (`ingestion.acquire`).

The network paths (`download_omw`, `fetch_kaikki`) are not exercised; only the
manifest round-trip and the path/lookup helpers are unit-tested.
"""

from pathlib import Path

import pytest

from lang_tools.lexicon.ingestion.acquire import UnknownKaikkiLanguageError
from lang_tools.lexicon.ingestion.acquire import fetch_kaikki
from lang_tools.lexicon.ingestion.acquire import kaikki_path
from lang_tools.lexicon.ingestion.acquire import manifest_path
from lang_tools.lexicon.ingestion.acquire import raw_dir
from lang_tools.lexicon.ingestion.acquire import read_manifest
from lang_tools.lexicon.ingestion.acquire import write_manifest


def test_raw_and_kaikki_paths(tmp_path: Path) -> None:
    assert raw_dir(tmp_path) == tmp_path / "_raw" / "lexicon"
    assert kaikki_path(tmp_path, "pt").name == "kaikki_pt.jsonl"


def test_manifest_round_trip_stamps_built_at(tmp_path: Path) -> None:
    assert read_manifest(tmp_path) is None  # nothing written yet
    path = write_manifest(tmp_path, {"languages": ["en"], "counts": {"concepts": 3}})
    assert path == manifest_path(tmp_path)
    loaded = read_manifest(tmp_path)
    assert loaded is not None
    assert loaded["languages"] == ["en"]
    assert loaded["counts"] == {"concepts": 3}
    assert "built_at" in loaded


def test_unknown_kaikki_language_raises(tmp_path: Path) -> None:
    with pytest.raises(UnknownKaikkiLanguageError):
        fetch_kaikki(["xx"], data_fol=tmp_path)
