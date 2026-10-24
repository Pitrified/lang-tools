"""Lexical ingestion pipelines.

Two layers live here:

- **Lemma-level loaders** (the original surface): parse a single external file
  into thin `Lemma` objects (`load_csv`, `load_static_list`) plus the merge/dedup
  helpers.
- **The phase-5 initial-build pipeline** (`acquire` -> `transform` -> `pipeline`):
  acquire the raw OMW backbone into a reproducible cache, transform it into
  source-tagged `concepts`/`lemmas`/`senses`, write the source-of-truth Parquet,
  and carve a committed sample slice. OMW is the sole source (the kaikki
  enrichment leg was removed in phase 5.5); the optional LLM granularity pass is
  a deferred seam.

Public API:
    load_csv: parse a brazilian-bites style CSV into `Lemma` objects.
    load_static_list: parse a worldly-words style minimal list.
    merge_lemmas: merge two `Lemma` records that share the same `(text, language)`.
    deduplicate: collapse an iterable of `Lemma`s into a unique-by-id list.
    build_initial: run the one-time initial build (the phase-5 entry point).
    transform: OMW backbone -> source-tagged lexical tables.
    carve_sample: slice a small committed sample from the full tables.
    TaggedTables: the five tables with parallel provenance tags.
"""

from lang_tools.lexicon.ingestion.csv_loader import load_csv
from lang_tools.lexicon.ingestion.dedup import deduplicate
from lang_tools.lexicon.ingestion.dedup import merge_lemmas
from lang_tools.lexicon.ingestion.pipeline import BuildSummary
from lang_tools.lexicon.ingestion.pipeline import build_initial
from lang_tools.lexicon.ingestion.sample import carve_sample
from lang_tools.lexicon.ingestion.static_list import load_static_list
from lang_tools.lexicon.ingestion.transform import TaggedTables
from lang_tools.lexicon.ingestion.transform import transform

__all__ = [
    "BuildSummary",
    "TaggedTables",
    "build_initial",
    "carve_sample",
    "deduplicate",
    "load_csv",
    "load_static_list",
    "merge_lemmas",
    "transform",
]
