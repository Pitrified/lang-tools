"""CEFR / graded-vocabulary staging - a validation list, not a shipped source.

Phase 5.54 Topic 5 needs ground-truth difficulty labels to test which complexity
signals carry. A graded list (CEFR A1-C2, or any difficulty scale) supplies that,
but only for **validation** - it is never merged into the corpus, so its license
(even share-alike / non-commercial) constrains nothing we ship.

There is no single clean multilingual CEFR list for en/pt/es/fr/it (see
`05.4_data_quality/other_datasets.md`). `KNOWN_CEFR_SOURCES` records the real,
grounded candidates and how to read each; `download_cefr_source` fetches and parses
a registered source (the Kelly ``.xls`` lists are read directly via ``xlrd``).
`download_cefr_list` handles any delimited (CSV/TSV) URL, and `stage_cefr_list`
parses one already on disk. The list choice - and accepting its license for
validation use - stays an explicit, recorded decision, not a hidden default.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlsplit
from urllib.request import Request
from urllib.request import urlopen

from loguru import logger as lg

from lang_tools.lexicon.ingestion.deps import OptionalDependencyMissingError
from lang_tools.lexicon.ingestion.staging.base import StagedDataset
from lang_tools.lexicon.ingestion.staging.base import dataset_dir
from lang_tools.lexicon.ingestion.staging.base import write_rows_parquet

if TYPE_CHECKING:
    from collections.abc import Iterable

#: Columns of the staged graded-vocabulary table.
CEFR_COLUMNS = ("word", "level")

#: Characters to strip from a level value (Kelly wraps levels in curly quotes).
_LEVEL_STRIP = " \t\"'“”"

_DOWNLOAD_TIMEOUT_S = 120
_USER_AGENT = "lang-tools-staging/0.1 (+https://github.com/Pitrified)"


@dataclass(frozen=True)
class CefrSource:
    """A known graded-vocabulary source and how to read it.

    Attributes:
        name: Registry key.
        languages: ISO 639-1 codes the source covers.
        url: Download URL (``""`` when there is no clean direct download).
        fmt: ``"xls"`` / ``"csv"`` / ``"tsv"`` (auto-parsed) or ``"pdf"``
            (no parser; guidance only).
        word_col: Header/column name holding the word.
        level_col: Header/column name holding the CEFR level.
        license: License of the source list.
        notes: Caveats - coverage gaps, ship/no-ship.
    """

    name: str
    languages: tuple[str, ...]
    url: str
    fmt: str
    word_col: str
    level_col: str
    license: str
    notes: str


#: Grounded candidate graded lists (verified 2026-06-21). Licenses are mostly
#: non-commercial / share-alike, which is fine for **validation-only** use (never
#: merged). There is no permissive multilingual CEFR list, and pt/es/fr have no
#: Kelly/CEFRLex coverage - those fall back to estimated bands (phase 6).
KNOWN_CEFR_SOURCES: dict[str, CefrSource] = {
    "kelly-en": CefrSource(
        name="kelly-en",
        languages=("en",),
        url="https://ssharoff.github.io/kelly/en_m3.xls",
        fmt="xls",
        word_col="Word",
        level_col="CEFR",
        license="CC-BY-NC-SA-2.0",
        notes="Leeds Kelly (xls, read via xlrd); CEFR A1-C2, validation-only",
    ),
    "kelly-it": CefrSource(
        name="kelly-it",
        languages=("it",),
        url="https://ssharoff.github.io/kelly/it_m3.xls",
        fmt="xls",
        word_col="Lemma",  # the it sheet differs from en: Lemma/Pos/Points
        level_col="Points",  # the it "Points" column holds the CEFR band (A1-C2)
        license="CC-BY-NC-SA-2.0",
        notes="Leeds Kelly (xls); CEFR in 'Points'; some lemmas are comma-lists",
    ),
    "oxford-en": CefrSource(
        name="oxford-en",
        languages=("en",),
        url="",
        fmt="pdf",
        word_col="",
        level_col="",
        license="restrictive (Oxford)",
        notes="Oxford 3000/5000 by CEFR; PDF, guidance only, do not ship or auto-parse",
    ),
}


class UnknownCefrSourceError(KeyError):
    """Raised when a CEFR source name is not in `KNOWN_CEFR_SOURCES`."""

    def __init__(self, name: str) -> None:
        """Initialize with the unknown source name.

        Args:
            name: The requested source key.
        """
        super().__init__(
            f"Unknown CEFR source {name!r} (known: {sorted(KNOWN_CEFR_SOURCES)}).",
        )
        self.name = name


class UndownloadableCefrSourceError(ValueError):
    """Raised when a registered CEFR source has no parseable download."""

    def __init__(self, source: CefrSource) -> None:
        """Initialize with the offending source.

        Args:
            source: The source with no URL or no auto-parsable format.
        """
        super().__init__(
            f"CEFR source {source.name!r} ({source.fmt}) has no auto-download: "
            f"{source.notes}",
        )
        self.source = source


class MissingCefrColumnError(KeyError):
    """Raised when a graded-list row lacks the configured word/level column."""

    def __init__(self, column: str, available: Iterable[str]) -> None:
        """Initialize with the missing column and what was available.

        Args:
            column: The configured column name that was not found.
            available: The column names the row actually had.
        """
        super().__init__(
            f"Graded list has no {column!r} column (found: {sorted(available)}).",
        )
        self.column = column


def parse_cefr_rows(
    rows: Iterable[dict[str, str]],
    *,
    word_col: str = "word",
    level_col: str = "level",
) -> list[dict[str, str]]:
    """Normalize raw graded-list dict rows to ``(word, level)`` rows.

    Args:
        rows: Raw rows (e.g. from `csv.DictReader`); each must carry the configured
            word and level columns.
        word_col: Source column holding the word form.
        level_col: Source column holding the difficulty level (e.g. ``"A1"``).

    Returns:
        Cleaned rows with empty-word entries dropped and levels upper-cased.

    Raises:
        MissingCefrColumnError: When a row lacks the word or level column.
    """
    cleaned: list[dict[str, str]] = []
    for row in rows:
        for col in (word_col, level_col):
            if col not in row:
                raise MissingCefrColumnError(col, row.keys())
        word = (row[word_col] or "").strip()
        if not word:
            continue
        cleaned.append({"word": word, "level": _clean_level(row[level_col])})
    return cleaned


def _clean_level(value: str | None) -> str:
    """Normalize a level cell to a bare upper-case band (strips quotes/whitespace).

    Kelly stores levels as ``“A1”`` (curly quotes); other lists use plain text.
    """
    return (value or "").strip(_LEVEL_STRIP).upper()


def stage_cefr_list(
    source_path: Path,
    *,
    language: str,
    data_fol: Path,
    word_col: str = "word",
    level_col: str = "level",
    delimiter: str = ",",
    license_name: str = "source-dependent (verify before use)",
    license_url: str = "",
) -> StagedDataset:
    """Stage a user-provided graded list to ``<staging>/cefr/<language>.parquet``.

    Args:
        source_path: Path to the graded list on disk (CSV/TSV with a header).
        language: ISO 639-1 code the list is for.
        data_fol: Project data folder; the staging cache lives under it.
        word_col: Header name of the word column in the source.
        level_col: Header name of the level column in the source.
        delimiter: Field delimiter of the source file (comma or tab).
        license_name: License of the source list (recorded for the audit; the list
            is validation-only and never shipped).
        license_url: Where the source list's license lives.

    Returns:
        The `StagedDataset` provenance record for the written table.

    Raises:
        MissingCefrColumnError: When the source lacks the configured columns.
    """
    with source_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        rows = parse_cefr_rows(reader, word_col=word_col, level_col=level_col)
    out = dataset_dir(data_fol, "cefr") / f"{language}.parquet"
    count = write_rows_parquet(rows, out, columns=CEFR_COLUMNS)
    lg.info("Staged {} graded-vocab rows for {} -> {}", count, language, out)
    return StagedDataset(
        name=f"cefr:{language}",
        source=f"graded list {source_path.name}",
        version="local file",
        license=license_name,
        license_url=license_url,
        path=str(out.relative_to(data_fol)),
        row_count=count,
        notes="validation-only difficulty labels; never merged into the corpus",
    )


def download_cefr_list(
    url: str,
    *,
    language: str,
    data_fol: Path,
    word_col: str = "word",
    level_col: str = "level",
    delimiter: str = ",",
    license_name: str = "source-dependent (verify before use)",
    license_url: str = "",
) -> StagedDataset:
    """Download a delimited (CSV/TSV) graded list and stage it.

    Makes "find a list on the internet" a one call for any delimited URL: it
    fetches the file into ``<staging>/cefr/_raw/`` and parses it with the same
    `parse_cefr_rows` core. Excel/PDF sources (e.g. the Kelly ``.xls`` in
    `KNOWN_CEFR_SOURCES`) are not delimited - convert them to CSV first and use
    `stage_cefr_list`. Network-isolated and not unit-tested.

    Args:
        url: HTTPS URL of a CSV/TSV graded list with a header row.
        language: ISO 639-1 code the list is for.
        data_fol: Project data folder; the staging cache lives under it.
        word_col: Header name of the word column.
        level_col: Header name of the level column.
        delimiter: Field delimiter of the source file (comma or tab).
        license_name: License of the source list (recorded; validation-only).
        license_url: Where the source list's license lives.

    Returns:
        The `StagedDataset` provenance record for the written table.

    Raises:
        MissingCefrColumnError: When the source lacks the configured columns.
    """
    raw_dir = dataset_dir(data_fol, "cefr") / "_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{language}{_suffix(url)}"
    lg.info("Downloading graded list for {} from {}", language, url)
    raw_path.write_bytes(_download_bytes(url))
    staged = stage_cefr_list(
        raw_path,
        language=language,
        data_fol=data_fol,
        word_col=word_col,
        level_col=level_col,
        delimiter=delimiter,
        license_name=license_name,
        license_url=license_url,
    )
    lg.info("Staged graded list for {} ({} rows)", language, staged.row_count)
    return staged


def _suffix(url: str) -> str:
    """Return the path suffix of a URL (``.csv`` / ``.tsv``), or ``.csv``."""
    suffix = Path(urlsplit(url).path).suffix
    return suffix or ".csv"


def _download_bytes(url: str) -> bytes:
    """Fetch a URL over HTTPS and return its bytes (scheme-checked)."""
    if urlsplit(url).scheme != "https":
        msg = f"Refusing non-HTTPS staging download: {url!r}"
        raise ValueError(msg)
    request = Request(url, headers={"User-Agent": _USER_AGENT})  # noqa: S310 - https checked
    with urlopen(request, timeout=_DOWNLOAD_TIMEOUT_S) as response:  # noqa: S310 - https checked
        return response.read()


def read_xls_cefr_rows(
    path: Path,
    *,
    word_col: str,
    level_col: str,
) -> list[dict[str, str]]:
    """Read ``(word, level)`` rows from a legacy ``.xls`` graded list via ``xlrd``.

    The first sheet's first row is the header. Numeric cells (ids, points) are
    coerced to text so the header lookup is uniform. ``xlrd`` is part of the lazy
    ``enrich`` extra.

    Args:
        path: Local ``.xls`` file (e.g. a downloaded Kelly list).
        word_col: Header label of the word column.
        level_col: Header label of the level column.

    Returns:
        Cleaned ``(word, level)`` rows (via `parse_cefr_rows`).

    Raises:
        OptionalDependencyMissingError: When ``xlrd`` is not installed.
        MissingCefrColumnError: When the header lacks the configured columns.
    """
    xlrd = _require_xlrd()
    book = xlrd.open_workbook(str(path))
    sheet = book.sheet_by_index(0)
    header = [str(sheet.cell_value(0, c)).strip() for c in range(sheet.ncols)]
    rows = [
        {header[c]: str(sheet.cell_value(r, c)) for c in range(sheet.ncols)}
        for r in range(1, sheet.nrows)
    ]
    return parse_cefr_rows(rows, word_col=word_col, level_col=level_col)


def _require_xlrd():  # noqa: ANN202 - the xlrd module, kept lazy
    """Import ``xlrd`` lazily, mapping absence to a clear error."""
    try:
        import xlrd  # noqa: PLC0415 - lazy so the extra stays optional  # pyright: ignore[reportMissingImports]
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        package, extra = "xlrd", "enrich"
        raise OptionalDependencyMissingError(package, extra) from exc
    return xlrd


def download_cefr_source(name: str, *, data_fol: Path) -> StagedDataset:
    """Download and stage a registered CEFR source by name (auto-parsed).

    Resolves `name` in `KNOWN_CEFR_SOURCES`, downloads it into
    ``<staging>/cefr/_raw/``, and parses it by its declared format (``xls`` via
    ``xlrd``, ``csv``/``tsv`` via the delimited reader). Network-isolated.

    Args:
        name: A key of `KNOWN_CEFR_SOURCES` (e.g. ``"kelly-en"``).
        data_fol: Project data folder; the staging cache lives under it.

    Returns:
        The `StagedDataset` provenance record for the staged language.

    Raises:
        UnknownCefrSourceError: When `name` is not registered.
        UndownloadableCefrSourceError: When the source has no parseable download
            (e.g. the PDF-only Oxford entry).
        OptionalDependencyMissingError: When an ``xls`` source needs ``xlrd``.
    """
    try:
        source = KNOWN_CEFR_SOURCES[name]
    except KeyError as exc:
        raise UnknownCefrSourceError(name) from exc
    if not source.url or source.fmt not in {"xls", "csv", "tsv"}:
        raise UndownloadableCefrSourceError(source)

    language = source.languages[0]
    raw_dir = dataset_dir(data_fol, "cefr") / "_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{name}.{source.fmt}"
    lg.info("Downloading CEFR source {} from {}", name, source.url)
    raw_path.write_bytes(_download_bytes(source.url))

    if source.fmt == "xls":
        rows = read_xls_cefr_rows(
            raw_path,
            word_col=source.word_col,
            level_col=source.level_col,
        )
    else:
        delimiter = "\t" if source.fmt == "tsv" else ","
        with raw_path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            rows = parse_cefr_rows(
                reader,
                word_col=source.word_col,
                level_col=source.level_col,
            )

    out = dataset_dir(data_fol, "cefr") / f"{language}.parquet"
    count = write_rows_parquet(rows, out, columns=CEFR_COLUMNS)
    lg.info("Staged {} CEFR rows for {} (source {}) -> {}", count, language, name, out)
    return StagedDataset(
        name=f"cefr:{language}",
        source=f"{name} ({source.url})",
        version="download date",
        license=source.license,
        license_url="",
        path=str(out.relative_to(data_fol)),
        row_count=count,
        notes=f"validation-only; {source.notes}",
    )
