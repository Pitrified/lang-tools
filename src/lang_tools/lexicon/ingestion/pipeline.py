"""Pipeline: the one-time initial build (acquire? -> transform -> write -> sample).

`build_initial` is the single entry point that turns the OMW backbone into the
source-of-truth Parquet under ``data/lexicon/`` plus a small committed sample
slice. It is linear by design (the source-of-truth model has no base/overlay
split): read sources, transform, write each table through the codec with its
provenance tags, write the ``_build.json`` manifest, then carve and write the
sample.

Sources can be supplied directly (tests, or a notebook that already loaded them)
or read from the raw cache produced by `acquire`. The heavy ``wn`` work lives in
`acquire`; this module only wires stages together, so it is fully testable with
in-memory inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
import shutil
from typing import TYPE_CHECKING

from loguru import logger as lg

from lang_tools.lexicon.codec import LEXICON_SUBDIR
from lang_tools.lexicon.codec import _dump_table
from lang_tools.lexicon.ingestion.acquire import write_manifest
from lang_tools.lexicon.ingestion.sample import DEFAULT_SAMPLE_CONCEPTS
from lang_tools.lexicon.ingestion.sample import carve_sample
from lang_tools.lexicon.ingestion.sources.cili import load_cili_glosses
from lang_tools.lexicon.ingestion.sources.omw import wn_synset_entries
from lang_tools.lexicon.ingestion.transform import TaggedTables
from lang_tools.lexicon.ingestion.transform import transform
from lang_tools.lexicon.maintenance import apply_gloss_overrides
from lang_tools.lexicon.maintenance import load_gloss_overrides

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping
    from pathlib import Path

    from lang_tools.lexicon.ingestion.sources.omw import SynsetEntry


@dataclass
class BuildSummary:
    """Row counts and the manifest path produced by a build.

    Attributes:
        languages: The languages built.
        counts: Per-table row counts in the full output.
        sample_counts: Per-table row counts in the carved sample slice.
        manifest_path: Where the ``_build.json`` manifest was written.
        gloss_overrides_applied: Curated gloss overrides applied to this build
            (phase 05.58).
        gloss_overrides_stale: Curated overrides naming a concept id this build
            does not contain; logged and skipped, never fatal.
    """

    languages: list[str]
    counts: dict[str, int]
    sample_counts: dict[str, int]
    manifest_path: Path
    gloss_overrides_applied: int = 0
    gloss_overrides_stale: int = 0


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
) -> tuple[list[SynsetEntry], dict[str, str]]:
    """Read the OMW backbone and CILI gloss map from the raw cache.

    OMW is the backbone (it creates the rows); CILI is an annotator keyed by ILI
    id (the permissive English-gloss fallback). Both read the same ``wn`` cache;
    each is loaded by its own single-responsibility adapter (phase 5.5 Step 3).
    The backbone is materialized (bounded, needed in full to build the tables);
    the CILI map is a small ``{ili_id: gloss}`` dict.

    Args:
        langs: ISO 639-1 codes to read.
        data_fol: Project data folder; the raw cache lives under it.

    Returns:
        The OMW synset entries and the CILI gloss map for the requested languages.
    """
    langs = list(langs)
    wn_dir = str(_wn_data_dir(data_fol))
    omw_entries = list(wn_synset_entries(langs, data_dir=wn_dir))
    cili_glosses = load_cili_glosses(data_dir=wn_dir)
    return omw_entries, cili_glosses


def _wn_data_dir(data_fol: Path) -> Path:
    """Return the ``wn`` data directory inside the raw cache (see `acquire`)."""
    from lang_tools.lexicon.ingestion.acquire import raw_dir  # noqa: PLC0415

    return raw_dir(data_fol) / "wn_data"


def build_initial(
    langs: Iterable[str],
    *,
    data_fol: Path,
    omw_entries: Iterable[SynsetEntry] | None = None,
    cili_glosses: Mapping[str, str] | None = None,
    sample_data_fol: Path | None = None,
    max_sample_concepts: int = DEFAULT_SAMPLE_CONCEPTS,
    extra_manifest: dict | None = None,
) -> BuildSummary:
    """Run the initial build: transform sources -> Parquet + manifest + sample.

    Args:
        langs: ISO 639-1 codes being built.
        data_fol: Project data folder; the source-of-truth Parquet is written
            under ``<data_fol>/lexicon/``.
        omw_entries: OMW synset entries; when ``None`` they (and `cili_glosses`)
            are read from the raw cache under `data_fol` (requires the ``ingest``
            extra).
        cili_glosses: ``{ili_id: english_gloss}`` map for the English-gloss
            fallback; when ``None`` and `omw_entries` is also ``None`` it is read
            from the cache. Pass it explicitly (with `omw_entries`) to exercise
            the fallback from in-memory inputs.
        sample_data_fol: When given, the carved sample slice is written there as
            its own Parquet corpus (e.g. a tmp dir the test/seed consumes).
        max_sample_concepts: Concept cap for the carved sample.
        extra_manifest: Extra fields merged into the manifest (e.g. the acquire
            fragments pinning source versions).

    Returns:
        A `BuildSummary` with row counts, the manifest path, and how many curated
        gloss overrides were applied.
    """
    langs = list(langs)
    if omw_entries is None:
        omw_entries, loaded_cili = load_sources(langs, data_fol=data_fol)
        if cili_glosses is None:
            cili_glosses = loaded_cili

    tables = transform(omw_entries, cili_glosses)
    # Curated gloss repairs are re-applied here so a rebuild reproduces them; a
    # post-hoc Parquet edit would be silently reverted by this very build (05.58).
    applied, stale = apply_gloss_overrides(
        tables.concepts,
        tables.concept_sources,
        overrides=load_gloss_overrides(data_fol),
    )
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

    manifest = {
        "languages": langs,
        "counts": counts,
        "gloss_overrides": {"applied": applied, "stale": stale},
        **(extra_manifest or {}),
    }
    path = write_manifest(data_fol, manifest)
    lg.info("Initial build complete: {} (sample {})", counts, sample_counts)

    return BuildSummary(
        languages=langs,
        counts=counts,
        sample_counts=sample_counts,
        manifest_path=path,
        gloss_overrides_applied=applied,
        gloss_overrides_stale=stale,
    )
