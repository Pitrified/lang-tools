"""Shared staging scaffolding: paths, the staged-dataset record, manifest, IO.

Phase 5.54 Stage 0 pulls each enrichment-candidate dataset into a tidy, read-only
cache under ``data/_raw/lexicon/staging/`` before any exploration, so the topic
notebooks read clean inputs instead of re-downloading and re-parsing. This module
holds the bits every staging adapter shares; the per-dataset loaders live beside
it (`tatoeba`, `frequency`, `wikidata`, `cefr`).

Staging never writes the source-of-truth Parquet under ``data/lexicon/``; it only
populates the gitignored raw cache and records what it pulled (source, version,
license) in a ``_staging.json`` manifest, so the licensing posture (phase 10) is
auditable from the cache alone.
"""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import UTC
from datetime import datetime
import json
from typing import TYPE_CHECKING
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

#: Gitignored staging subdirectory of the data folder (regenerable, not LFS). It
#: sits under the existing ``_raw/lexicon`` cache so all raw inputs share one root.
STAGING_SUBDIR = "_raw/lexicon/staging"

#: Manifest filename written under the staging dir (records what was pulled).
STAGING_MANIFEST_NAME = "_staging.json"

#: Known licenses for the candidate datasets, recorded so phase 10 can audit the
#: posture from the staging manifest alone. Value is ``(license, url)``.
KNOWN_LICENSES: dict[str, tuple[str, str]] = {
    "tatoeba": ("CC-BY-2.0-FR", "https://tatoeba.org/eng/terms_of_use"),
    "wikidata": ("CC0-1.0", "https://www.wikidata.org/wiki/Wikidata:Licensing"),
    "wordfreq": (
        "MIT code; mixed-corpus data (verify per language)",
        "https://github.com/rspeer/wordfreq",
    ),
    "cili": ("CC-BY-4.0", "https://github.com/globalwordnet/cili"),
    "cefr": ("source-dependent (verify before shipping)", ""),
}


class EnrichDependencyMissingError(ImportError):
    """Raised when a staging path needs the ``enrich`` extra (e.g. ``wordfreq``)."""

    def __init__(self, package: str = "wordfreq") -> None:
        """Initialize with install guidance.

        Args:
            package: The missing optional package in the ``enrich`` extra.
        """
        super().__init__(
            f"This staging path needs the 'enrich' extra ({package}). Install it "
            f"with `uv sync --extra enrich`.",
        )
        self.package = package


def staging_dir(data_fol: Path) -> Path:
    """Return the staging cache directory under a data folder."""
    return data_fol / STAGING_SUBDIR


def dataset_dir(data_fol: Path, name: str) -> Path:
    """Return (creating) the per-dataset directory under the staging cache.

    Args:
        data_fol: Project data folder.
        name: Dataset folder name (e.g. ``"tatoeba"``, ``"frequency"``).

    Returns:
        The created ``<staging>/<name>`` directory.
    """
    path = staging_dir(data_fol) / name
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass(frozen=True)
class StagedDataset:
    """One staged dataset's provenance record (a manifest entry).

    Attributes:
        name: Stable key, dataset plus any partition (e.g. ``"frequency:en"``).
        source: Human-readable source name.
        version: Version or snapshot date pinning what was pulled.
        license: License of the staged data.
        license_url: Where the license terms live.
        path: Path to the staged artifact relative to the data folder, or ``""``
            when the dataset is staged elsewhere (e.g. OMW via ``wn``).
        row_count: Number of rows staged (``-1`` when not applicable).
        notes: Free-text caveats (sense-blindness, coverage, corpus mix, ...).
    """

    name: str
    source: str
    version: str
    license: str
    license_url: str
    path: str
    row_count: int
    notes: str = ""


def write_rows_parquet(
    rows: Sequence[dict[str, Any]],
    path: Path,
    *,
    columns: Sequence[str],
) -> int:
    """Write tidy dict rows to a zstd Parquet file; return the row count.

    A thin writer for the staging tables (frequency lists, Tatoeba sentences, ...).
    It is deliberately schema-light - these are exploration inputs, not the typed
    source-of-truth tables the codec owns - but uses the same zstd compression the
    corpus does.

    Args:
        rows: The rows to write; every row must carry every column in `columns`.
        path: Destination ``.parquet`` file (its parent must already exist).
        columns: Column order for the written table.

    Returns:
        The number of rows written.
    """
    table = pa.Table.from_pylist(list(rows))
    # Reorder to the requested column order when all are present.
    if set(columns).issubset(set(table.column_names)):
        table = table.select(list(columns))
    pq.write_table(table, path, compression="zstd")
    return table.num_rows


def write_staging_manifest(
    data_fol: Path,
    datasets: Sequence[StagedDataset],
) -> Path:
    """Write the staging manifest, stamping a UTC ``staged_at`` timestamp.

    Args:
        data_fol: Project data folder.
        datasets: The staged-dataset records to record.

    Returns:
        The path the manifest was written to.
    """
    path = staging_dir(data_fol) / STAGING_MANIFEST_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "staged_at": datetime.now(UTC).isoformat(),
        "datasets": [asdict(d) for d in datasets],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def read_staging_manifest(data_fol: Path) -> dict[str, Any] | None:
    """Read the staging manifest, or ``None`` when nothing has been staged yet."""
    path = staging_dir(data_fol) / STAGING_MANIFEST_NAME
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass
class StagingResult:
    """The outcome of a staging run: the records plus the manifest location.

    Attributes:
        datasets: One `StagedDataset` per artifact staged this run.
        manifest_path: Where the staging manifest was written.
    """

    datasets: list[StagedDataset] = field(default_factory=list)
    manifest_path: Path | None = None
