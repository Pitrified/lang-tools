"""Parquet codec seam for the lexical corpus (the on-disk format boundary).

Per the phase-3 decision the canonical format is **Parquet (zstd)**, every
table, with the large tables (`lemmas` / `senses`) partitioned per language and
all of it under git-LFS. This module is the only place that touches the on-disk
format: `_load_table` / `_dump_table` hide it behind a stable signature so the
rest of the store imports the seam, never ``pyarrow``.

``pyarrow`` is a **base** dependency: reading the Parquet corpus is the store's
only load path, so the columnar engine is always available. It is still imported
lazily inside the functions here to keep module import cheap. ``duckdb`` (the
``store`` extra) backs the inspect/QA path only; a caller that reaches it without
the extra installed gets a clear `StoreDependencyMissingError`.

On-disk layout under ``<data_fol>/lexicon/``:

    lemmas/<lang>.parquet          # partitioned per language
    senses/<lang>.parquet          # partitioned per language (else _all.parquet)
    concepts.parquet               # single file
    false_friends.parquet          # single file
    concept_relations.parquet      # single file

The persisted shape is **lean**: only the source fields plus the computed ``id``
(kept as an index column). Cosmetic computed fields (`has_accent`,
`accented_chars`, `length`) and the store-hydrated back-references (`senses`,
`concepts`, `lemma`, ...) are excluded - the latter automatically, via their
``exclude=True`` field spec.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.lemma import Lemma
from lang_tools.lexicon.relations import ConceptRelation
from lang_tools.lexicon.relations import FalseFriendRelation
from lang_tools.lexicon.sense import Sense

if TYPE_CHECKING:
    from pathlib import Path

    from pydantic import BaseModel

#: Subdirectory of the data folder holding the whole lexical corpus.
LEXICON_SUBDIR = "lexicon"

#: Tables stored one Parquet file per language (the large ones).
PARTITIONED: frozenset[str] = frozenset({"lemmas", "senses"})

#: Lightweight per-row provenance column (``omw|kaikki|llm|manual``). It is the
#: one seam a future re-ingestion merge needs (refresh machine rows, preserve
#: ``manual`` ones), so it lives **on disk only**: written as an extra Parquet
#: column when a provenance-aware dump supplies it, and always dropped on load so
#: it never reaches the thin pydantic models (same trick as the computed ``id``).
PROVENANCE_COL = "source"

#: Model class backing each table.
_MODELS: dict[str, type[BaseModel]] = {
    "lemmas": Lemma,
    "concepts": Concept,
    "senses": Sense,
    "false_friends": FalseFriendRelation,
    "concept_relations": ConceptRelation,
}

#: Ordered persisted columns per table (the pyarrow schema field order).
_COLUMNS: dict[str, list[str]] = {
    "lemmas": [
        "id",
        "text",
        "language",
        "normalized",
        "part_of_speech",
        "topics",
        "examples",
        "sources",
    ],
    "concepts": ["id", "definitions"],
    "senses": [
        "id",
        "lemma_id",
        "concept_id",
        "token_frequency",
        "sense_frequency",
        "frequency_is_estimated",
        "cefr_level",
        "cefr_is_estimated",
    ],
    "false_friends": [
        "lemma_id_a",
        "lemma_id_b",
        "similarity_score",
        "explanation_notes",
    ],
    "concept_relations": ["concept_id_a", "concept_id_b", "relation_type"],
}

#: Columns stored as a Parquet ``map<string,string>`` (read back as a dict).
_MAP_COLUMNS: dict[str, frozenset[str]] = {
    "concepts": frozenset({"definitions"}),
    "false_friends": frozenset({"explanation_notes"}),
}

#: Columns the constructor does not accept (computed) and must be dropped on load.
_DROP_ON_LOAD: dict[str, frozenset[str]] = {
    "lemmas": frozenset({"id"}),
    "concepts": frozenset(),
    "senses": frozenset({"id"}),
    "false_friends": frozenset(),
    "concept_relations": frozenset(),
}


class ProvenanceLengthMismatchError(ValueError):
    """Raised when a provenance-aware dump gets the wrong number of source tags."""

    def __init__(self, name: str, n_models: int, n_sources: int) -> None:
        """Initialize with the table and the two mismatched lengths.

        Args:
            name: The table being dumped.
            n_models: Number of models passed.
            n_sources: Number of source tags passed.
        """
        super().__init__(
            f"{name}: got {n_sources} source tags for {n_models} models "
            "(they must be parallel).",
        )
        self.name = name
        self.n_models = n_models
        self.n_sources = n_sources


class UnknownTableError(KeyError):
    """Raised when a table name is not one of the known lexical tables."""

    def __init__(self, name: str) -> None:
        """Initialize with the offending table name.

        Args:
            name: The unrecognized table name.
        """
        super().__init__(f"Unknown lexical table: {name!r} (known: {sorted(_MODELS)})")
        self.name = name


class StoreDependencyMissingError(ImportError):
    """Raised when the inspect/QA path is used without the optional ``store`` extra."""

    def __init__(self) -> None:
        """Initialize with install guidance."""
        super().__init__(
            "This path needs the 'store' extra (duckdb). Install it with "
            "`uv sync --extra store`.",
        )


class MalformedRecordError(ValueError):
    """Raised when a stored row cannot be parsed into its table's model."""

    def __init__(self, name: str, row: dict[str, Any], cause: Exception) -> None:
        """Initialize with the table, the offending row, and the cause.

        Args:
            name: The table the row belongs to.
            row: The raw row that failed validation.
            cause: The underlying validation error.
        """
        super().__init__(f"Malformed {name} record: {row!r} ({cause})")
        self.name = name
        self.row = row
        self.cause = cause


def _require_pyarrow() -> tuple[Any, Any]:
    """Import ``pyarrow`` lazily, mapping absence to a clear error.

    Returns:
        The ``pyarrow`` and ``pyarrow.parquet`` modules.

    Raises:
        StoreDependencyMissingError: When ``pyarrow`` is not installed.
    """
    try:
        import pyarrow as pa  # noqa: PLC0415 - lazy so the extra stays optional
        import pyarrow.parquet as pq  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise StoreDependencyMissingError from exc
    return pa, pq


def _schema(name: str) -> Any:  # noqa: ANN401 - pyarrow.Schema, kept lazy
    """Build the pyarrow schema for a table (lazy, so pyarrow stays optional)."""
    pa, _ = _require_pyarrow()
    example = pa.struct([("sentence", pa.string()), ("translation", pa.string())])
    str_map = pa.map_(pa.string(), pa.string())
    schemas = {
        "lemmas": pa.schema(
            [
                ("id", pa.string()),
                ("text", pa.string()),
                ("language", pa.string()),
                ("normalized", pa.string()),
                ("part_of_speech", pa.string()),
                ("topics", pa.list_(pa.string())),
                ("examples", pa.list_(example)),
                ("sources", pa.list_(pa.string())),
            ],
        ),
        "concepts": pa.schema([("id", pa.string()), ("definitions", str_map)]),
        "senses": pa.schema(
            [
                ("id", pa.string()),
                ("lemma_id", pa.string()),
                ("concept_id", pa.string()),
                ("token_frequency", pa.float64()),
                ("sense_frequency", pa.float64()),
                ("frequency_is_estimated", pa.bool_()),
                ("cefr_level", pa.string()),
                ("cefr_is_estimated", pa.bool_()),
            ],
        ),
        "false_friends": pa.schema(
            [
                ("lemma_id_a", pa.string()),
                ("lemma_id_b", pa.string()),
                ("similarity_score", pa.float64()),
                ("explanation_notes", str_map),
            ],
        ),
        "concept_relations": pa.schema(
            [
                ("concept_id_a", pa.string()),
                ("concept_id_b", pa.string()),
                ("relation_type", pa.string()),
            ],
        ),
    }
    return schemas[name]


def _schema_with_source(name: str) -> Any:  # noqa: ANN401 - pyarrow.Schema, kept lazy
    """Return a table's schema with the trailing `PROVENANCE_COL` string field."""
    pa, _ = _require_pyarrow()
    return _schema(name).append(pa.field(PROVENANCE_COL, pa.string()))


def model_class(name: str) -> type[BaseModel]:
    """Return the model class backing a table.

    Args:
        name: Table name.

    Returns:
        The pydantic model class for the table.

    Raises:
        UnknownTableError: If `name` is not a known table.
    """
    if name not in _MODELS:
        raise UnknownTableError(name)
    return _MODELS[name]


def row_from_model(name: str, model: BaseModel) -> dict[str, Any]:
    """Project a model down to its lean persisted row (Parquet column order).

    Args:
        name: Table the model belongs to.
        model: The model instance to serialize.

    Returns:
        A dict holding exactly the persisted columns for the table.
    """
    dumped = model.model_dump()
    return {col: dumped.get(col) for col in _COLUMNS[name]}


def model_from_row(name: str, row: dict[str, Any]) -> BaseModel:
    """Build a model from a stored row, normalizing map columns.

    Args:
        name: Table the row belongs to.
        row: The raw row (e.g. from Parquet ``to_pylist`` or JSONL).

    Returns:
        The validated model instance.

    Raises:
        MalformedRecordError: If the row fails model validation.
    """
    drop = _DROP_ON_LOAD[name] | {PROVENANCE_COL}
    cleaned = {k: v for k, v in row.items() if k not in drop}
    for col in _MAP_COLUMNS.get(name, frozenset()):
        value = cleaned.get(col)
        # pyarrow reads a map<string,string> back as a list of (k, v) tuples.
        if value is None:
            cleaned[col] = {}
        elif not isinstance(value, dict):
            cleaned[col] = dict(value)
    try:
        return model_class(name).model_validate(cleaned)
    except ValueError as exc:
        raise MalformedRecordError(name, row, exc) from exc


def _table_dir(data_fol: Path) -> Path:
    """Return the corpus directory under a data folder."""
    return data_fol / LEXICON_SUBDIR


def _read_parquet(path: Path) -> list[dict[str, Any]]:
    """Read one Parquet file into a list of raw row dicts (empty if missing)."""
    if not path.exists():
        return []
    _, pq = _require_pyarrow()
    return pq.read_table(path).to_pylist()


def _table_paths(name: str, data_fol: Path, lang: str | None = None) -> list[Path]:
    """Return the Parquet file path(s) backing a table (partition-aware).

    Args:
        name: Table name (see `PARTITIONED` for the per-language ones).
        data_fol: Project data folder; the corpus lives under ``<data_fol>/lexicon/``.
        lang: For a partitioned table, restrict to this language's file.

    Returns:
        The candidate Parquet paths (some may not exist yet).
    """
    table_dir = _table_dir(data_fol)
    if name in PARTITIONED:
        part_dir = table_dir / name
        if lang is not None:
            return [part_dir / f"{lang}.parquet"]
        if part_dir.exists():
            return sorted(part_dir.glob("*.parquet"))
        return []
    return [table_dir / f"{name}.parquet"]


def _read_table_rows(
    name: str,
    *,
    data_fol: Path,
    lang: str | None = None,
) -> list[dict[str, Any]]:
    """Read a table's raw Parquet rows across its partitions (no model build)."""
    rows: list[dict[str, Any]] = []
    for path in _table_paths(name, data_fol, lang):
        rows.extend(_read_parquet(path))
    return rows


def _load_table(
    name: str,
    *,
    data_fol: Path,
    lang: str | None = None,
) -> list[Any]:
    """Load a table from Parquet into validated models.

    Args:
        name: Table name (see `PARTITIONED` for the per-language ones).
        data_fol: Project data folder; the corpus lives under
            ``<data_fol>/lexicon/``.
        lang: For a partitioned table, read only this language's file. Ignored
            for single-file tables.

    Returns:
        The validated models, or an empty list when the file(s) do not exist.

    Raises:
        UnknownTableError: If `name` is not a known table.
        MalformedRecordError: If a stored row fails validation.
    """
    if name not in _MODELS:
        raise UnknownTableError(name)
    rows = _read_table_rows(name, data_fol=data_fol, lang=lang)
    return [model_from_row(name, row) for row in rows]


def load_raw_table(
    name: str,
    *,
    data_fol: Path,
    lang: str | None = None,
) -> list[dict[str, Any]]:
    """Load a table's lean persisted rows from Parquet **without building models**.

    This is the fast/lean store-load path: it skips the pydantic validate+dump
    round-trip `_load_table` pays (the profiling in phase 5.3 showed that retaining
    every model is what drives the load's memory peak). Each returned row holds
    exactly the persisted columns (`_COLUMNS[name]`), the on-disk provenance column
    dropped and any ``map<string,string>`` column normalized to a plain dict.

    Args:
        name: Table name (see `PARTITIONED` for the per-language ones).
        data_fol: Project data folder; the corpus lives under ``<data_fol>/lexicon/``.
        lang: For a partitioned table, read only this language's file.

    Returns:
        The lean raw rows, or an empty list when the file(s) do not exist.

    Raises:
        UnknownTableError: If `name` is not a known table.
    """
    if name not in _MODELS:
        raise UnknownTableError(name)
    cols = _COLUMNS[name]
    maps = _MAP_COLUMNS.get(name, frozenset())
    out: list[dict[str, Any]] = []
    for row in _read_table_rows(name, data_fol=data_fol, lang=lang):
        clean: dict[str, Any] = {}
        for col in cols:
            value = row.get(col)
            if col in maps and value is not None and not isinstance(value, dict):
                # pyarrow reads a map<string,string> back as a list of (k, v) tuples.
                value = dict(value)
            clean[col] = value
        out.append(clean)
    return out


def _write_parquet(path: Path, rows: list[dict[str, Any]], schema: Any) -> None:  # noqa: ANN401
    """Write raw rows to one Parquet file (zstd), creating parent dirs."""
    pa, pq = _require_pyarrow()
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows, schema=schema)
    pq.write_table(table, path, compression="zstd")


def _dump_table(
    name: str,
    models: list[Any],
    *,
    data_fol: Path,
    lang: str | None = None,
    sources: list[str] | None = None,
) -> None:
    """Write a table of models to Parquet (zstd).

    Partitioned tables are split per language: `lemmas` by each lemma's
    ``language`` field; `senses` only when `lang` is supplied (otherwise a
    single ``_all.parquet``, since a sense's language is a join the ingestion
    phase owns), so the seam never guesses.

    Args:
        name: Table name.
        models: The model instances to persist.
        data_fol: Project data folder.
        lang: Force a single per-language file for a partitioned table.
        sources: Optional parallel list of per-row provenance tags
            (``omw|kaikki|llm|manual``); when given, an extra `PROVENANCE_COL`
            column is written and stays with each row through partitioning. The
            tag is always dropped on load, so it never reaches the models.

    Raises:
        UnknownTableError: If `name` is not a known table.
        ProvenanceLengthMismatchError: If `sources` is given but not parallel to
            `models`.
    """
    if name not in _MODELS:
        raise UnknownTableError(name)
    table_dir = _table_dir(data_fol)
    rows = [row_from_model(name, m) for m in models]

    if sources is None:
        schema = _schema(name)
    else:
        if len(sources) != len(rows):
            raise ProvenanceLengthMismatchError(name, len(rows), len(sources))
        for row, tag in zip(rows, sources, strict=True):
            row[PROVENANCE_COL] = tag
        schema = _schema_with_source(name)

    if name not in PARTITIONED:
        _write_parquet(table_dir / f"{name}.parquet", rows, schema)
        return

    part_dir = table_dir / name
    if lang is not None:
        _write_parquet(part_dir / f"{lang}.parquet", rows, schema)
        return
    if name == "lemmas":
        by_lang: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            by_lang.setdefault(row["language"], []).append(row)
        for lang_code, lang_rows in by_lang.items():
            _write_parquet(part_dir / f"{lang_code}.parquet", lang_rows, schema)
        return
    _write_parquet(part_dir / "_all.parquet", rows, schema)
