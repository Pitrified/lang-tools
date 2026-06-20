"""Token-frequency staging - a per-language word-frequency list via ``wordfreq``.

`wordfreq` gives a per-language frequency rank for word forms, drawn from a mixed
corpus (subtitles, web text, ...). This is the **language-level** frequency signal
of phase 5.54 Topic 3: how common a *word form* is in one language, distinct from
the concept-level commonness SemCor carries. Staging it here lets the SemCor
exploration correlate concept commonness against an independent per-language list.

The frequency rows are a flat ``(word, rank, zipf)`` table per language. ``wordfreq``
is an optional dependency (the ``enrich`` extra) and is imported lazily, so the
base package and the runtime never pull it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger as lg

from lang_tools.lexicon.ingestion.staging.base import KNOWN_LICENSES
from lang_tools.lexicon.ingestion.staging.base import EnrichDependencyMissingError
from lang_tools.lexicon.ingestion.staging.base import StagedDataset
from lang_tools.lexicon.ingestion.staging.base import dataset_dir
from lang_tools.lexicon.ingestion.staging.base import write_rows_parquet

if TYPE_CHECKING:
    from pathlib import Path

#: Re-exported so existing callers keep importing it from this module.
__all__ = ["EnrichDependencyMissingError", "frequency_rows", "stage_frequency_list"]

#: Default number of top word forms to stage per language.
DEFAULT_TOP_N = 50_000

#: Columns of the staged frequency table.
FREQUENCY_COLUMNS = ("word", "rank", "zipf")


def _require_wordfreq():  # noqa: ANN202 - the wordfreq module, kept lazy
    """Import ``wordfreq`` lazily, mapping absence to a clear error."""
    try:
        import wordfreq  # noqa: PLC0415 - lazy so the extra stays optional  # pyright: ignore[reportMissingImports]
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        package = "wordfreq"
        raise EnrichDependencyMissingError(package) from exc
    return wordfreq


def frequency_rows(lang: str, *, top_n: int = DEFAULT_TOP_N) -> list[dict[str, object]]:
    """Return the top-`top_n` word forms for `lang` as ``(word, rank, zipf)`` rows.

    Rank is 1-based by descending frequency (rank 1 is the most frequent word);
    zipf is ``wordfreq``'s log-scaled frequency (higher is more common).

    Args:
        lang: ISO 639-1 code ``wordfreq`` supports (e.g. ``"en"``, ``"it"``).
        top_n: How many top forms to take.

    Returns:
        One row per word form, ordered by ascending rank.

    Raises:
        EnrichDependencyMissingError: When the ``enrich`` extra is not installed.
    """
    wordfreq = _require_wordfreq()
    words = wordfreq.top_n_list(lang, top_n)
    return [
        {"word": word, "rank": rank, "zipf": wordfreq.zipf_frequency(word, lang)}
        for rank, word in enumerate(words, start=1)
    ]


def stage_frequency_list(
    lang: str,
    *,
    data_fol: Path,
    top_n: int = DEFAULT_TOP_N,
) -> StagedDataset:
    """Stage a per-language frequency list to ``<staging>/frequency/<lang>.parquet``.

    Args:
        lang: ISO 639-1 code to stage.
        data_fol: Project data folder; the staging cache lives under it.
        top_n: How many top word forms to stage.

    Returns:
        The `StagedDataset` provenance record for the written table.

    Raises:
        EnrichDependencyMissingError: When the ``enrich`` extra is not installed.
    """
    rows = frequency_rows(lang, top_n=top_n)
    out = dataset_dir(data_fol, "frequency") / f"{lang}.parquet"
    count = write_rows_parquet(rows, out, columns=FREQUENCY_COLUMNS)
    licence, url = KNOWN_LICENSES["wordfreq"]
    lg.info("Staged {} frequency rows for {} -> {}", count, lang, out)
    return StagedDataset(
        name=f"frequency:{lang}",
        source="wordfreq",
        version=_wordfreq_version(),
        license=licence,
        license_url=url,
        path=str(out.relative_to(data_fol)),
        row_count=count,
        notes="language-level token frequency; mixed corpus, data license varies",
    )


def _wordfreq_version() -> str:
    """Return the installed ``wordfreq`` version (or ``"unknown"``)."""
    wordfreq = _require_wordfreq()
    return getattr(wordfreq, "__version__", "unknown")
