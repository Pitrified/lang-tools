"""Word ingestion pipelines.

Public API:
    load_wiktionary_jsonl: parse a kaikki.org JSONL dump into `Word` objects.
    WikiRecord, WikiSense: typed shapes for kaikki.org records.
    load_csv: parse a brazilian-bites style CSV into `Word` objects.
    load_static_list: parse a worldly-words style minimal list.
    merge_words: merge two `Word` records that share the same `(text, language)`.
    deduplicate: collapse an iterable of `Word`s into a unique-by-id list.
"""

from lang_tools.words.ingestion.csv_loader import load_csv
from lang_tools.words.ingestion.dedup import deduplicate
from lang_tools.words.ingestion.dedup import merge_words
from lang_tools.words.ingestion.static_list import load_static_list
from lang_tools.words.ingestion.wiktionary import WikiRecord
from lang_tools.words.ingestion.wiktionary import WikiSense
from lang_tools.words.ingestion.wiktionary import load_wiktionary_jsonl

__all__ = [
    "WikiRecord",
    "WikiSense",
    "deduplicate",
    "load_csv",
    "load_static_list",
    "load_wiktionary_jsonl",
    "merge_words",
]
