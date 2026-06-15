"""Lemma ingestion pipelines.

Public API:
    load_wiktionary_jsonl: parse a kaikki.org JSONL dump into `Lemma` objects.
    WikiRecord, WikiSense: typed shapes for kaikki.org records.
    load_csv: parse a brazilian-bites style CSV into `Lemma` objects.
    load_static_list: parse a worldly-words style minimal list.
    merge_lemmas: merge two `Lemma` records that share the same `(text, language)`.
    deduplicate: collapse an iterable of `Lemma`s into a unique-by-id list.
"""

from lang_tools.lexicon.ingestion.csv_loader import load_csv
from lang_tools.lexicon.ingestion.dedup import deduplicate
from lang_tools.lexicon.ingestion.dedup import merge_lemmas
from lang_tools.lexicon.ingestion.static_list import load_static_list
from lang_tools.lexicon.ingestion.wiktionary import WikiRecord
from lang_tools.lexicon.ingestion.wiktionary import WikiSense
from lang_tools.lexicon.ingestion.wiktionary import load_wiktionary_jsonl

__all__ = [
    "WikiRecord",
    "WikiSense",
    "deduplicate",
    "load_csv",
    "load_static_list",
    "load_wiktionary_jsonl",
    "merge_lemmas",
]
