"""Wikidata Lexemes staging - the CC0 lexeme dump, plus a gentle SPARQL probe.

Wikidata Lexemes are the CC0 structured-sense candidate of phase 5.54 Topic 3 /
the deferred Wikidata leg. There are two access paths, and they are not equal:

- The **lexeme dump** (`latest-lexemes.json.gz`, ~590 MB, CC0) is the viable bulk
  source: complete, rate-limit-free, and exact counts fall out for free. This is
  the recommended path - `stream_lexeme_dump` / `parse_lexeme_dump_records` /
  `stage_wikidata_lexeme_dump`.
- The public **SPARQL endpoint** (`query.wikidata.org`) is heavily throttled - a
  global ``COUNT`` over all lexemes times out / returns HTTP 429 (~1 request per
  minute observed). So `probe_wikidata_lexemes` is a *gentle* fallback: it backs
  off on 429 (honouring ``Retry-After``) and skips the expensive count by default.

The query builders, the dump parser, and the result flatteners are pure and
unit-tested; the HTTP download / SPARQL request are network-isolated and not tested.
"""

from __future__ import annotations

import bz2
import gzip
import json
from pathlib import Path
import time
from typing import TYPE_CHECKING
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.parse import urlsplit
from urllib.request import Request
from urllib.request import urlopen

from loguru import logger as lg

from lang_tools.lexicon.ingestion.staging.base import KNOWN_LICENSES
from lang_tools.lexicon.ingestion.staging.base import StagedDataset
from lang_tools.lexicon.ingestion.staging.base import dataset_dir
from lang_tools.lexicon.ingestion.staging.base import write_rows_parquet

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Iterator

#: Public Wikidata Query Service SPARQL endpoint.
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"

#: CC0 lexeme dump (the rate-limit-free bulk source; ~590 MB gzipped).
WIKIDATA_LEXEME_DUMP_URL = (
    "https://dumps.wikimedia.org/wikidatawiki/entities/latest-lexemes.json.gz"
)

#: ISO 639-1 -> Wikidata language item, used as ``dct:language wd:<item>``.
WIKIDATA_LANG_ITEMS: dict[str, str] = {
    "en": "Q1860",
    "pt": "Q5146",
    "es": "Q1321",
    "fr": "Q150",
    "it": "Q652",
}

#: Columns of the staged lexeme-sample table.
LEXEME_COLUMNS = ("lexeme", "lemma", "category")

#: Default sample size for the per-language probe.
DEFAULT_SAMPLE_LIMIT = 200

_REQUEST_TIMEOUT_S = 120
_USER_AGENT = "lang-tools-staging/0.1 (+https://github.com/Pitrified)"

#: SPARQL retry policy for the throttled public endpoint (HTTP 429).
_MAX_RETRIES = 4
_DEFAULT_BACKOFF_S = 60
_HTTP_TOO_MANY_REQUESTS = 429

_PREFIXES = (
    "PREFIX ontolex: <http://www.w3.org/ns/lemon/ontolex#>\n"
    "PREFIX dct: <http://purl.org/dc/terms/>\n"
    "PREFIX wikibase: <http://wikiba.se/ontology#>\n"
    "PREFIX wd: <http://www.wikidata.org/entity/>\n"
)


class UnknownWikidataLanguageError(KeyError):
    """Raised when no Wikidata language item is mapped for a language code."""

    def __init__(self, language: str) -> None:
        """Initialize with the unsupported language code.

        Args:
            language: The ISO 639-1 code with no mapped Wikidata language item.
        """
        super().__init__(
            f"No Wikidata language item known for {language!r} "
            f"(known: {sorted(WIKIDATA_LANG_ITEMS)}).",
        )
        self.language = language


def _lang_item(lang: str) -> str:
    """Return the Wikidata language item for a language code, or raise."""
    try:
        return WIKIDATA_LANG_ITEMS[lang]
    except KeyError as exc:
        raise UnknownWikidataLanguageError(lang) from exc


def build_lexeme_count_query(lang_item: str) -> str:
    """Return a SPARQL query counting lexemes for a Wikidata language item.

    Args:
        lang_item: A Wikidata item id such as ``"Q1860"`` (English).

    Returns:
        The SPARQL query string.
    """
    return (
        _PREFIXES
        + "SELECT (COUNT(?l) AS ?count) WHERE {\n"
        + f"  ?l a ontolex:LexicalEntry ; dct:language wd:{lang_item} .\n"
        + "}"
    )


def build_lexeme_sample_query(lang_item: str, limit: int) -> str:
    """Return a SPARQL query for a sample of lexemes for a language item.

    Args:
        lang_item: A Wikidata item id such as ``"Q1860"`` (English).
        limit: Maximum number of lexemes to return.

    Returns:
        The SPARQL query string (lexeme id, lemma text, lexical category id).
    """
    return (
        _PREFIXES
        + "SELECT ?l ?lemma ?category WHERE {\n"
        + f"  ?l a ontolex:LexicalEntry ; dct:language wd:{lang_item} ;\n"
        + "     wikibase:lemma ?lemma .\n"
        + "  OPTIONAL { ?l wikibase:lexicalCategory ?category . }\n"
        + "}\n"
        + f"LIMIT {limit}"
    )


def probe_wikidata_lexemes(
    lang: str,
    *,
    data_fol: Path,
    limit: int = DEFAULT_SAMPLE_LIMIT,
    with_count: bool = False,
) -> StagedDataset:
    """Probe lexeme coverage for `lang` via SPARQL and stage a small sample.

    This is the gentle fallback to the dump (`stage_wikidata_lexeme_dump`): the
    public endpoint is throttled, and a global ``COUNT`` over all lexemes is the
    query that returns HTTP 429, so the count is **off by default**. The sample
    query (`limit` rows) is cheap. Network-isolated and not tested.

    Args:
        lang: ISO 639-1 code to probe (must be in `WIKIDATA_LANG_ITEMS`).
        data_fol: Project data folder; the staging cache lives under it.
        limit: Sample size to stage.
        with_count: When ``True``, also run the expensive total-count query (may
            be rate-limited). When ``False`` (default), ``row_count`` is the staged
            sample size and the total is left for the dump.

    Returns:
        The `StagedDataset` record for the staged sample.

    Raises:
        UnknownWikidataLanguageError: When the language has no Wikidata item.
    """
    item = _lang_item(lang)
    sample = _sample_rows(_sparql_get(build_lexeme_sample_query(item, limit)))
    out = dataset_dir(data_fol, "wikidata") / f"{lang}_sample.parquet"
    staged = write_rows_parquet(sample, out, columns=LEXEME_COLUMNS)
    total = (
        _count_from_result(_sparql_get(build_lexeme_count_query(item)))
        if with_count
        else -1
    )
    licence, url = KNOWN_LICENSES["wikidata"]
    note = (
        f"SPARQL sample of {staged}; total {total} lexemes"
        if with_count
        else f"SPARQL sample of {staged}; total via the dump (count off to avoid 429)"
    )
    lg.info("Wikidata {} probe: staged {}-row sample -> {}", lang, staged, out)
    return StagedDataset(
        name=f"wikidata:{lang}",
        source="Wikidata Lexemes (query.wikidata.org)",
        version="live query (probe date)",
        license=licence,
        license_url=url,
        path=str(out.relative_to(data_fol)),
        row_count=total if with_count else staged,
        notes=note,
    )


def _sparql_get(query: str) -> dict[str, Any]:
    """Run a SPARQL query against Wikidata, backing off on HTTP 429.

    The public endpoint rate-limits aggressively; on 429 this waits the server's
    ``Retry-After`` (or a default) and retries up to `_MAX_RETRIES` times before
    giving up, so a probe degrades into a slow success rather than a hard failure.
    """
    params = urlencode({"query": query, "format": "json"})
    src = f"{WIKIDATA_SPARQL_URL}?{params}"
    if urlsplit(src).scheme != "https":  # pragma: no cover - constant is https
        msg = f"Refusing non-HTTPS SPARQL request: {WIKIDATA_SPARQL_URL!r}"
        raise ValueError(msg)
    request = Request(  # noqa: S310 - https checked above
        src,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "application/sparql-results+json",
        },
    )
    for attempt in range(_MAX_RETRIES):
        try:
            with urlopen(request, timeout=_REQUEST_TIMEOUT_S) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code != _HTTP_TOO_MANY_REQUESTS or attempt == _MAX_RETRIES - 1:
                raise
            wait = _retry_after_seconds(exc)
            lg.warning("Wikidata 429; backing off {}s (attempt {})", wait, attempt + 1)
            time.sleep(wait)
    msg = "SPARQL retry loop exhausted"  # pragma: no cover - guarded by the raise above
    raise RuntimeError(msg)  # pragma: no cover


def _retry_after_seconds(exc: HTTPError) -> int:
    """Return the ``Retry-After`` seconds from a 429 response, or the default."""
    header = exc.headers.get("Retry-After") if exc.headers else None
    if header and header.isdigit():
        return int(header)
    return _DEFAULT_BACKOFF_S


def _count_from_result(result: dict[str, Any]) -> int:
    """Extract the integer ``?count`` from a SPARQL count result."""
    bindings = result.get("results", {}).get("bindings", [])
    if not bindings:
        return 0
    return int(bindings[0]["count"]["value"])


def _sample_rows(result: dict[str, Any]) -> list[dict[str, str]]:
    """Flatten a SPARQL lexeme-sample result to ``(lexeme, lemma, category)`` rows."""
    return [
        {
            "lexeme": binding.get("l", {}).get("value", ""),
            "lemma": binding.get("lemma", {}).get("value", ""),
            "category": binding.get("category", {}).get("value", ""),
        }
        for binding in result.get("results", {}).get("bindings", [])
    ]


# --- CC0 lexeme dump (the rate-limit-free bulk source) -----------------------

#: Read chunk for the streamed dump download (8 MiB).
_DOWNLOAD_CHUNK = 8 * 1024 * 1024
_DUMP_TIMEOUT_S = 600
_PROGRESS_EVERY_MB = 50


def download_lexeme_dump(
    *,
    data_fol: Path,
    url: str = WIKIDATA_LEXEME_DUMP_URL,
) -> Path:
    """Download the CC0 lexeme dump into the staging cache (streamed, resumable-skip).

    Streams to ``<staging>/wikidata/_raw/latest-lexemes.json.gz`` in chunks so the
    ~590 MB never sits in memory, and skips the download when a non-empty file is
    already there. Creates the directory (the cause of the manual ``curl`` failure).
    Network-isolated and not unit-tested.

    Args:
        data_fol: Project data folder; the staging cache lives under it.
        url: Dump URL (defaults to `WIKIDATA_LEXEME_DUMP_URL`).

    Returns:
        The local path to the downloaded dump.
    """
    raw_dir = dataset_dir(data_fol, "wikidata") / "_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    dest = raw_dir / Path(urlsplit(url).path).name
    if dest.exists() and dest.stat().st_size > 0:
        lg.info("Lexeme dump already present ({:.0f} MB)", dest.stat().st_size / 1e6)
        return dest
    if urlsplit(url).scheme != "https":  # pragma: no cover - constant is https
        msg = f"Refusing non-HTTPS dump download: {url!r}"
        raise ValueError(msg)
    lg.info("Downloading lexeme dump from {} -> {}", url, dest)
    request = Request(url, headers={"User-Agent": _USER_AGENT})  # noqa: S310 - https checked
    downloaded = 0
    next_mark = _PROGRESS_EVERY_MB
    with (
        urlopen(request, timeout=_DUMP_TIMEOUT_S) as response,  # noqa: S310 - https checked
        dest.open("wb") as handle,
    ):
        while chunk := response.read(_DOWNLOAD_CHUNK):
            handle.write(chunk)
            downloaded += len(chunk)
            if downloaded / 1e6 >= next_mark:
                lg.info("  ... {:.0f} MB", downloaded / 1e6)
                next_mark += _PROGRESS_EVERY_MB
    lg.success("Downloaded lexeme dump: {:.0f} MB -> {}", downloaded / 1e6, dest)
    return dest


# --- dump parsing ------------------------------------------------------------


def parse_lexeme_dump_records(
    records: Iterable[dict[str, Any]],
    langs: Iterable[str],
) -> Iterator[dict[str, str]]:
    """Yield ``(lang, lexeme, lemma, category)`` rows for `langs` from dump records.

    Each dump record is a Wikidata lexeme entity; its top-level ``language`` is the
    Wikidata item id (e.g. ``"Q1860"``), which is mapped back to our ISO code. Pure
    and unit-tested with small dicts (no download).

    Args:
        records: Parsed lexeme entity dicts (from `stream_lexeme_dump`).
        langs: ISO 639-1 codes to keep (each must be in `WIKIDATA_LANG_ITEMS`).

    Yields:
        One row per lexeme whose language is in `langs`.

    Raises:
        UnknownWikidataLanguageError: When a language has no Wikidata item.
    """
    item_to_lang = {_lang_item(lang): lang for lang in langs}
    for record in records:
        lang = item_to_lang.get(record.get("language", ""))
        if lang is None:
            continue
        yield {
            "lang": lang,
            "lexeme": record.get("id", ""),
            "lemma": _first_lemma(record.get("lemmas", {}), lang),
            "category": record.get("lexicalCategory", ""),
        }


def _first_lemma(lemmas: dict[str, Any], lang: str) -> str:
    """Return a lexeme's lemma text, preferring the matching language code."""
    if not lemmas:
        return ""
    preferred = lemmas.get(lang)
    if preferred:
        return preferred.get("value", "")
    return next(iter(lemmas.values())).get("value", "")


def stream_lexeme_dump(path: Path) -> Iterator[dict[str, Any]]:
    """Stream lexeme entity dicts from a ``latest-lexemes.json[.gz|.bz2]`` dump.

    The dump is a giant JSON array, one entity object per line wrapped by ``[`` and
    ``]`` lines, each line comma-terminated. Streaming line by line keeps the
    ~590 MB file from being held resident. Network-free (reads a local file).

    Args:
        path: Local path to the (optionally gz/bz2-compressed) dump.

    Yields:
        One parsed lexeme entity dict per line.
    """
    openers = {".gz": gzip.open, ".bz2": bz2.open}
    opener = openers.get(path.suffix, open)
    with opener(path, "rt", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip().rstrip(",")
            if not line or line in {"[", "]"}:
                continue
            yield json.loads(line)


def stage_wikidata_lexeme_dump(
    langs: Iterable[str],
    *,
    data_fol: Path,
    dump_path: Path,
) -> list[StagedDataset]:
    """Stage per-language lexeme tables from a local CC0 lexeme dump.

    Streams the dump once, partitions the lexemes for `langs`, and writes a
    ``<staging>/wikidata/<lang>.parquet`` of ``(lexeme, lemma, category)`` per
    language with exact counts. This is the recommended path (no rate limit).

    Args:
        langs: ISO 639-1 codes to stage (each in `WIKIDATA_LANG_ITEMS`).
        data_fol: Project data folder; the staging cache lives under it.
        dump_path: Local path to the lexeme dump (download it first, see
            `WIKIDATA_LEXEME_DUMP_URL`).

    Returns:
        One `StagedDataset` per language staged.

    Raises:
        UnknownWikidataLanguageError: When a language has no Wikidata item.
    """
    langs = list(langs)
    by_lang: dict[str, list[dict[str, str]]] = {lang: [] for lang in langs}
    records = parse_lexeme_dump_records(stream_lexeme_dump(dump_path), langs)
    for row in records:
        by_lang[row["lang"]].append(
            {
                "lexeme": row["lexeme"],
                "lemma": row["lemma"],
                "category": row["category"],
            },
        )
    out_dir = dataset_dir(data_fol, "wikidata")
    licence, url = KNOWN_LICENSES["wikidata"]
    staged: list[StagedDataset] = []
    for lang in langs:
        out = out_dir / f"{lang}.parquet"
        count = write_rows_parquet(by_lang[lang], out, columns=LEXEME_COLUMNS)
        lg.info("Staged {} Wikidata lexemes for {} -> {}", count, lang, out)
        staged.append(
            StagedDataset(
                name=f"wikidata:{lang}",
                source="Wikidata Lexemes (CC0 dump)",
                version="latest-lexemes (dump date)",
                license=licence,
                license_url=url,
                path=str(out.relative_to(data_fol)),
                row_count=count,
                notes="full per-language lexeme set from the CC0 dump",
            ),
        )
    return staged
