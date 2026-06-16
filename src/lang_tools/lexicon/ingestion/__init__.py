"""Lexical ingestion pipelines.

Two layers live here:

- **Lemma-level loaders** (the original surface): parse a single external file
  into thin `Lemma` objects (`load_csv`, `load_static_list`, `load_wiktionary_jsonl`)
  plus the merge/dedup helpers.
- **The phase-5 initial-build pipeline** (`acquire` -> `transform` -> `pipeline`):
  acquire raw OMW + kaikki into a reproducible cache, transform them into
  source-tagged `concepts`/`lemmas`/`senses`, write the source-of-truth Parquet,
  and carve a committed sample slice. OMW is the concept backbone; kaikki is
  enrichment only; the optional LLM granularity pass is a deferred seam.

Public API:
    load_wiktionary_jsonl: parse a kaikki.org JSONL dump into `Lemma` objects.
    WikiRecord, WikiSense: typed shapes for kaikki.org records.
    load_csv: parse a brazilian-bites style CSV into `Lemma` objects.
    load_static_list: parse a worldly-words style minimal list.
    merge_lemmas: merge two `Lemma` records that share the same `(text, language)`.
    deduplicate: collapse an iterable of `Lemma`s into a unique-by-id list.
    build_initial: run the one-time initial build (the phase-5 entry point).
    transform: OMW + kaikki -> source-tagged lexical tables.
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
from lang_tools.lexicon.ingestion.wiktionary import WikiRecord
from lang_tools.lexicon.ingestion.wiktionary import WikiSense
from lang_tools.lexicon.ingestion.wiktionary import load_wiktionary_jsonl

__all__ = [
    "BuildSummary",
    "TaggedTables",
    "WikiRecord",
    "WikiSense",
    "build_initial",
    "carve_sample",
    "deduplicate",
    "load_csv",
    "load_static_list",
    "load_wiktionary_jsonl",
    "merge_lemmas",
    "transform",
]
