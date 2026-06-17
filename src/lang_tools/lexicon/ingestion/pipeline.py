"""Pipeline: the one-time initial build (acquire? -> transform -> write -> sample).

`build_initial` is the single entry point that turns the OMW backbone and kaikki
enrichment into the source-of-truth Parquet under ``data/lexicon/`` plus a small
committed sample slice. It is linear by design (the source-of-truth model has no
base/overlay split): read sources, transform, write each table through the codec
with its provenance tags, write the ``_build.json`` manifest, then carve and write
the sample.

Sources can be supplied directly (tests, or a notebook that already loaded them)
or read from the raw cache produced by `acquire`. The heavy ``wn``/HTTP work lives
in `acquire`; this module only wires stages together, so it is fully testable with
in-memory inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
import itertools
import shutil
from typing import TYPE_CHECKING

from loguru import logger as lg

from lang_tools.lexicon.codec import LEXICON_SUBDIR
from lang_tools.lexicon.codec import _dump_table
from lang_tools.lexicon.ingestion.acquire import kaikki_path
from lang_tools.lexicon.ingestion.acquire import write_manifest
from lang_tools.lexicon.ingestion.sample import DEFAULT_SAMPLE_CONCEPTS
from lang_tools.lexicon.ingestion.sample import carve_sample
from lang_tools.lexicon.ingestion.sources.kaikki import load_kaikki_entries
from lang_tools.lexicon.ingestion.sources.omw import wn_synset_entries
from lang_tools.lexicon.ingestion.transform import TaggedTables
from lang_tools.lexicon.ingestion.transform import transform

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Iterator
    from pathlib import Path

    from lang_tools.lexicon.ingestion.sources.kaikki import KaikkiEntry
    from lang_tools.lexicon.ingestion.sources.omw import SynsetEntry


@dataclass
class BuildSummary:
    """Row counts and the manifest path produced by a build.

    Attributes:
        languages: The languages built.
        counts: Per-table row counts in the full output.
        sample_counts: Per-table row counts in the carved sample slice.
        manifest_path: Where the ``_build.json`` manifest was written.
    """

    languages: list[str]
    counts: dict[str, int]
    sample_counts: dict[str, int]
    manifest_path: Path


def _clean_corpus_tables(data_fol: Path) -> None:
    """Remove existing table artifacts so a build writes a **fresh** corpus.

    Stops stale per-language partitions from a previous build (or an old seed run)
    lingering in the corpus dir. The ``_build.json`` manifest is left in place (it
    is overwritten afterwards); the ``_store.sqlite`` cache is dropped so the next
    store load rebuilds from the new Parquet.
    """
    lex = data_fol / LEXICON_SUBDIR
    if not lex.exists():
        return
    for partitioned in ("lemmas", "senses"):
        shutil.rmtree(lex / partitioned, ignore_errors=True)
    for single in ("concepts", "false_friends", "concept_relations"):
        (lex / f"{single}.parquet").unlink(missing_ok=True)
    # The persisted store cache (see lemma_store.STORE_DB_NAME) is now stale.
    for cache in ("_store.sqlite", "_store.sqlite.sig"):
        (lex / cache).unlink(missing_ok=True)


def _write_tables(tables: TaggedTables, data_fol: Path) -> dict[str, int]:
    """Write every table to Parquet with its provenance tags; return row counts.

    The corpus dir is cleared first so the build is a fresh write (no stale
    partitions). `lemmas` partition per language automatically (the codec reads
    each lemma's ``language``); `senses` are grouped per language here (a sense's
    language is its lemma's language - a join only ingestion knows) so each lands
    in its own partition file. The single-file tables are written as-is.
    """
    _clean_corpus_tables(data_fol)
    _dump_table(
        "lemmas",
        tables.lemmas,
        data_fol=data_fol,
        sources=tables.lemma_sources,
    )
    _dump_table(
        "concepts",
        tables.concepts,
        data_fol=data_fol,
        sources=tables.concept_sources,
    )
    _dump_senses_partitioned(tables, data_fol)
    _dump_table(
        "false_friends",
        tables.false_friends,
        data_fol=data_fol,
        sources=tables.false_friend_sources,
    )
    _dump_table(
        "concept_relations",
        tables.concept_relations,
        data_fol=data_fol,
        sources=tables.concept_relation_sources,
    )
    return {
        "lemmas": len(tables.lemmas),
        "concepts": len(tables.concepts),
        "senses": len(tables.senses),
        "false_friends": len(tables.false_friends),
        "concept_relations": len(tables.concept_relations),
    }


def _dump_senses_partitioned(tables: TaggedTables, data_fol: Path) -> None:
    """Write senses into per-language partition files, keyed by lemma language."""
    lang_by_lemma = {lemma.id: lemma.language for lemma in tables.lemmas}
    by_lang: dict[str, tuple[list, list[str]]] = {}
    for sense, tag in zip(tables.senses, tables.sense_sources, strict=True):
        lang = lang_by_lemma.get(sense.lemma_id, "_all")
        models, tags = by_lang.setdefault(lang, ([], []))
        models.append(sense)
        tags.append(tag)
    for lang, (models, tags) in by_lang.items():
        _dump_table("senses", models, data_fol=data_fol, lang=lang, sources=tags)


def load_sources(
    langs: Iterable[str],
    *,
    data_fol: Path,
) -> tuple[list[SynsetEntry], Iterator[KaikkiEntry]]:
    """Read OMW + kaikki from the raw cache into source records.

    The OMW backbone is materialized (bounded, needed in full to derive the join
    keys); the kaikki dumps are returned as a **lazy** chained iterator so each
    multi-hundred-MB file is streamed and filtered line-by-line by `transform`
    rather than held resident (the kaikki OOM fix). Do not ``list()`` the second
    element.

    Args:
        langs: ISO 639-1 codes to read.
        data_fol: Project data folder; the raw cache lives under it.

    Returns:
        The OMW synset entries (a list) and a lazy iterator over the kaikki
        enrichment entries across all languages.
    """
    langs = list(langs)
    omw_entries = list(wn_synset_entries(langs, data_dir=str(_wn_data_dir(data_fol))))
    kaikki_streams: list[Iterator[KaikkiEntry]] = []
    for language in langs:
        path = kaikki_path(data_fol, language)
        if path.exists():
            kaikki_streams.append(load_kaikki_entries(path, language))
        else:
            lg.warning("No cached kaikki dump for {} at {}", language, path)
    return omw_entries, itertools.chain.from_iterable(kaikki_streams)


def _wn_data_dir(data_fol: Path) -> Path:
    """Return the ``wn`` data directory inside the raw cache (see `acquire`)."""
    from lang_tools.lexicon.ingestion.acquire import raw_dir  # noqa: PLC0415

    return raw_dir(data_fol) / "wn_data"


def build_initial(
    langs: Iterable[str],
    *,
    data_fol: Path,
    omw_entries: Iterable[SynsetEntry] | None = None,
    kaikki_entries: Iterable[KaikkiEntry] | None = None,
    sample_data_fol: Path | None = None,
    max_sample_concepts: int = DEFAULT_SAMPLE_CONCEPTS,
    extra_manifest: dict | None = None,
) -> BuildSummary:
    """Run the initial build: transform sources -> Parquet + manifest + sample.

    Args:
        langs: ISO 639-1 codes being built.
        data_fol: Project data folder; the source-of-truth Parquet is written
            under ``<data_fol>/lexicon/``.
        omw_entries: OMW synset entries; when ``None`` they are read from the raw
            cache under `data_fol` (requires the ``ingest`` extra).
        kaikki_entries: kaikki enrichment entries; when ``None`` they are read
            from the raw cache (absent dumps are simply skipped).
        sample_data_fol: When given, the carved sample slice is written there as
            its own Parquet corpus (e.g. a tmp dir the test/seed consumes).
        max_sample_concepts: Concept cap for the carved sample.
        extra_manifest: Extra fields merged into the manifest (e.g. the acquire
            fragments pinning source versions).

    Returns:
        A `BuildSummary` with row counts and the manifest path.
    """
    langs = list(langs)
    if omw_entries is None or kaikki_entries is None:
        loaded_omw, loaded_kaikki = load_sources(langs, data_fol=data_fol)
        omw_entries = loaded_omw if omw_entries is None else omw_entries
        kaikki_entries = loaded_kaikki if kaikki_entries is None else kaikki_entries

    tables = transform(omw_entries, kaikki_entries)
    counts = _write_tables(tables, data_fol)

    sample = carve_sample(tables, max_concepts=max_sample_concepts)
    sample_counts = {
        "lemmas": len(sample.lemmas),
        "concepts": len(sample.concepts),
        "senses": len(sample.senses),
        "false_friends": len(sample.false_friends),
        "concept_relations": len(sample.concept_relations),
    }
    if sample_data_fol is not None:
        _write_tables(sample, sample_data_fol)

    manifest = {"languages": langs, "counts": counts, **(extra_manifest or {})}
    path = write_manifest(data_fol, manifest)
    lg.info("Initial build complete: {} (sample {})", counts, sample_counts)

    return BuildSummary(
        languages=langs,
        counts=counts,
        sample_counts=sample_counts,
        manifest_path=path,
    )
