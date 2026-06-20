"""Stage 0 dataset staging for the phase 5.54 data-enrichment exploration.

One staging adapter per candidate dataset, each pulling a read-only, tidy copy
into ``data/_raw/lexicon/staging/`` so the topic notebooks read clean inputs
instead of re-downloading and re-parsing. The contract mirrors the `sources`
adapters but for *exploration* inputs rather than the build:

- Staging **never** writes the source-of-truth Parquet under ``data/lexicon/``; it
  only populates the gitignored raw cache and a ``_staging.json`` manifest.
- Every staged dataset records its license in that manifest, so the phase-10
  licensing posture is auditable from the cache alone.
- Network and optional-dependency work is isolated in the impure functions; the
  parsers, query builders, and index builders are pure and unit-tested.

Adapter registry:

- `tatoeba` - example sentences (CC-BY); sense-blind lemma join, examples only.
- `frequency` - per-language token frequency via ``wordfreq`` (``enrich`` extra).
- `wikidata` - CC0 lexeme coverage probe (count + small sample), no full pull.
- `cefr` - a user-provided graded list, staged for **validation only**.

OMW and CILI are already staged by `acquire.download_omw` (into the ``wn`` cache);
`omw_cili_staged_records` records them in the staging manifest for completeness.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lang_tools.lexicon.ingestion.staging.base import KNOWN_LICENSES
from lang_tools.lexicon.ingestion.staging.base import STAGING_SUBDIR
from lang_tools.lexicon.ingestion.staging.base import StagedDataset
from lang_tools.lexicon.ingestion.staging.base import StagingResult
from lang_tools.lexicon.ingestion.staging.base import dataset_dir
from lang_tools.lexicon.ingestion.staging.base import read_staging_manifest
from lang_tools.lexicon.ingestion.staging.base import staging_dir
from lang_tools.lexicon.ingestion.staging.base import write_rows_parquet
from lang_tools.lexicon.ingestion.staging.base import write_staging_manifest
from lang_tools.lexicon.ingestion.staging.cefr import KNOWN_CEFR_SOURCES
from lang_tools.lexicon.ingestion.staging.cefr import CefrSource
from lang_tools.lexicon.ingestion.staging.cefr import download_cefr_list
from lang_tools.lexicon.ingestion.staging.cefr import download_cefr_source
from lang_tools.lexicon.ingestion.staging.cefr import stage_cefr_list
from lang_tools.lexicon.ingestion.staging.frequency import stage_frequency_list
from lang_tools.lexicon.ingestion.staging.tatoeba import build_lemma_sentence_index
from lang_tools.lexicon.ingestion.staging.tatoeba import download_tatoeba_sentences
from lang_tools.lexicon.ingestion.staging.tatoeba import lemma_forms_by_language
from lang_tools.lexicon.ingestion.staging.tatoeba import parse_tatoeba_tsv
from lang_tools.lexicon.ingestion.staging.wikidata import download_lexeme_dump
from lang_tools.lexicon.ingestion.staging.wikidata import probe_wikidata_lexemes
from lang_tools.lexicon.ingestion.staging.wikidata import stage_wikidata_lexeme_dump

if TYPE_CHECKING:
    from collections.abc import Iterable


def omw_cili_staged_records(langs: Iterable[str]) -> list[StagedDataset]:
    """Return manifest records for OMW + CILI (staged by `acquire.download_omw`).

    Staging does not re-download OMW/CILI - they live in the ``wn`` cache that the
    build already populates - but the staging manifest should still record them so
    the full enrichment input set and its licenses are in one place.

    Args:
        langs: ISO 639-1 codes that were downloaded.

    Returns:
        Two `StagedDataset` records (OMW backbone, CILI gloss resource).
    """
    cili_license, cili_url = KNOWN_LICENSES["cili"]
    langs = list(langs)
    return [
        StagedDataset(
            name="omw",
            source="Open Multilingual Wordnet (via wn)",
            version="1.4",
            license="per-lexicon, permissive (verify each)",
            license_url="https://omwn.org/",
            path="_raw/lexicon/wn_data",
            row_count=-1,
            notes=f"backbone, already staged by acquire.download_omw for {langs}",
        ),
        StagedDataset(
            name="cili",
            source="Collaborative Interlingual Index (via wn)",
            version="1.0",
            license=cili_license,
            license_url=cili_url,
            path="_raw/lexicon/wn_data",
            row_count=-1,
            notes="English ILI glosses, already staged by acquire.download_omw",
        ),
    ]


__all__ = [
    "KNOWN_CEFR_SOURCES",
    "KNOWN_LICENSES",
    "STAGING_SUBDIR",
    "CefrSource",
    "StagedDataset",
    "StagingResult",
    "build_lemma_sentence_index",
    "dataset_dir",
    "download_cefr_list",
    "download_cefr_source",
    "download_lexeme_dump",
    "download_tatoeba_sentences",
    "lemma_forms_by_language",
    "omw_cili_staged_records",
    "parse_tatoeba_tsv",
    "probe_wikidata_lexemes",
    "read_staging_manifest",
    "stage_cefr_list",
    "stage_frequency_list",
    "stage_wikidata_lexeme_dump",
    "staging_dir",
    "write_rows_parquet",
    "write_staging_manifest",
]
