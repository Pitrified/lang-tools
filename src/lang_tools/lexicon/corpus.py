"""Inspect / edit tooling for the Parquet corpus (read-only QA + validated edits).

Nothing human-readable is committed (the corpus is Parquet under LFS), so
inspection and editing are explicit operations over the canonical files. All the
logic lives here as package functions; a thin notebook under the top-level
``notebooks/`` folder is only a caller. Three entry points:

- `inspect_table` - read-only DuckDB SQL over the Parquet, no import step.
  DuckDB is confined to this one function.
- `export_table` / `import_table` - the validated edit round-trip: export a table
  to a transient JSONL, hand/LLM-edit it, then re-import. The import validates
  **every row through the pydantic model** before rewriting the canonical
  Parquet, so a renamed/missing column or bad value fails loudly rather than
  corrupting the corpus. The JSONL is scratch, never committed.

Schema changes are **not** edits: adding or removing a column regenerates the
table from the ingestion pipeline (phase 5), per the "no data migration"
decision - never patched line-by-line.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from typing import Any

from lang_tools.lexicon.codec import LEXICON_SUBDIR
from lang_tools.lexicon.codec import PARTITIONED
from lang_tools.lexicon.codec import StoreDependencyMissingError
from lang_tools.lexicon.codec import _dump_table
from lang_tools.lexicon.codec import _load_table
from lang_tools.lexicon.codec import model_class
from lang_tools.lexicon.codec import model_from_row
from lang_tools.lexicon.codec import row_from_model

if TYPE_CHECKING:
    from pathlib import Path


def inspect_table(
    name: str,
    *,
    data_fol: Path,
    lang: str | None = None,
    where: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Run read-only DuckDB SQL over a table's Parquet and return the rows.

    Args:
        name: Table name.
        data_fol: Project data folder; the corpus lives under
            ``<data_fol>/lexicon/``.
        lang: For a partitioned table, restrict to one language's file.
        where: Optional SQL ``WHERE`` clause body (without the keyword).
        limit: Optional row cap.

    Returns:
        The selected rows as dicts. Empty when the Parquet file(s) are absent.

    Raises:
        StoreDependencyMissingError: When the optional ``store`` extra (duckdb)
            is not installed.
    """
    try:
        import duckdb  # noqa: PLC0415 - lazy so the extra stays optional
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise StoreDependencyMissingError from exc

    table_dir = data_fol / LEXICON_SUBDIR
    if name in PARTITIONED:
        glob = f"{lang}.parquet" if lang is not None else "*.parquet"
        source = table_dir / name / glob
    else:
        source = table_dir / f"{name}.parquet"

    sql = f"SELECT * FROM read_parquet('{source}')"  # noqa: S608 - paths are internal
    if where:
        sql += f" WHERE {where}"
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    con = duckdb.connect()
    try:
        result = con.execute(sql)
        columns = [d[0] for d in result.description]
        return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]
    finally:
        con.close()


def export_table(name: str, path: Path, *, data_fol: Path) -> int:
    """Export a table to a transient JSONL file for hand/LLM editing.

    Args:
        name: Table name.
        path: Destination JSONL path (scratch; never committed).
        data_fol: Project data folder.

    Returns:
        The number of rows written.
    """
    models = _load_table(name, data_fol=data_fol)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for model in models:
            fh.write(json.dumps(row_from_model(name, model), ensure_ascii=False))
            fh.write("\n")
    return len(models)


def import_table(name: str, path: Path, *, data_fol: Path) -> int:
    """Re-import an edited JSONL, validating every row, into the Parquet corpus.

    Each line is validated through the table's pydantic model (`model_from_row`),
    so a renamed/missing column or bad value raises `MalformedRecordError` before
    anything is written.

    Args:
        name: Table name.
        path: Source JSONL path produced by `export_table` and edited.
        data_fol: Project data folder.

    Returns:
        The number of rows imported.

    Raises:
        MalformedRecordError: If any edited row fails model validation.
    """
    # Validate the class exists up front (clear error on a bad table name).
    model_class(name)
    with path.open("r", encoding="utf-8") as fh:
        models = [
            model_from_row(name, json.loads(line))
            for line in fh
            if line.strip()
        ]
    _dump_table(name, models, data_fol=data_fol)
    return len(models)
