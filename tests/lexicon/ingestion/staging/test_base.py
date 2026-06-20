"""Tests for the staging scaffolding (`ingestion.staging.base`)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pyarrow.parquet as pq

from lang_tools.lexicon.ingestion.staging.base import StagedDataset
from lang_tools.lexicon.ingestion.staging.base import dataset_dir
from lang_tools.lexicon.ingestion.staging.base import read_staging_manifest
from lang_tools.lexicon.ingestion.staging.base import staging_dir
from lang_tools.lexicon.ingestion.staging.base import write_rows_parquet
from lang_tools.lexicon.ingestion.staging.base import write_staging_manifest

if TYPE_CHECKING:
    from pathlib import Path


def test_dataset_dir_is_created_under_staging(tmp_path: Path) -> None:
    out = dataset_dir(tmp_path, "frequency")
    assert out.is_dir()
    assert out == staging_dir(tmp_path) / "frequency"


def test_write_rows_parquet_round_trips_in_column_order(tmp_path: Path) -> None:
    rows = [
        {"word": "casa", "rank": 1, "zipf": 5.0},
        {"word": "gatto", "rank": 2, "zipf": 4.0},
    ]
    out = dataset_dir(tmp_path, "frequency") / "it.parquet"
    count = write_rows_parquet(rows, out, columns=("word", "rank", "zipf"))
    assert count == 2
    table = pq.read_table(out)
    assert table.column_names == ["word", "rank", "zipf"]
    assert table.column("word").to_pylist() == ["casa", "gatto"]


def test_manifest_round_trips(tmp_path: Path) -> None:
    assert read_staging_manifest(tmp_path) is None
    datasets = [
        StagedDataset(
            name="frequency:it",
            source="wordfreq",
            version="3.1.1",
            license="MIT",
            license_url="https://example.test",
            path="_raw/lexicon/staging/frequency/it.parquet",
            row_count=2,
        ),
    ]
    path = write_staging_manifest(tmp_path, datasets)
    assert path.exists()
    manifest = read_staging_manifest(tmp_path)
    assert manifest is not None
    assert "staged_at" in manifest
    assert manifest["datasets"][0]["name"] == "frequency:it"
    assert manifest["datasets"][0]["row_count"] == 2
