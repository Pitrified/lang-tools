"""Tests for the closed-class sense drop (`ingestion.closed_class`)."""

from typing import TYPE_CHECKING

from lang_tools.lexicon.ingestion.closed_class import CLOSED_CLASS
from lang_tools.lexicon.ingestion.closed_class import closed_class_drops
from lang_tools.lexicon.ingestion.form_review import apply_form_drops
from lang_tools.lexicon.ingestion.pipeline import build_initial
from lang_tools.lexicon.ingestion.sources.omw import SynsetEntry
from lang_tools.lexicon.ingestion.transform import transform
from lang_tools.lexicon.lemma_id import lemma_id
from lang_tools.lexicon.lemma_store import LexiconStore

if TYPE_CHECKING:
    from pathlib import Path


def _entries() -> list[SynsetEntry]:
    return [
        SynsetEntry(
            "en", "en-1", "i1", "to, toward, or in the east", ("eastward",), pos="r"
        ),
        SynsetEntry("pt", "pt-1", "i1", None, ("para", "para o leste"), pos="r"),
        SynsetEntry("en", "en-2", "i2", "a dwelling", ("house",), pos="n"),
        SynsetEntry("pt", "pt-2", "i2", None, ("casa",), pos="n"),
        SynsetEntry("en", "en-3", "i3", "a preposition-like noun", ("in",), pos="n"),
    ]


def test_closed_class_lemmas_lose_their_senses_and_content_words_stay() -> None:
    tables = transform(_entries())
    drops = closed_class_drops(tables)
    assert {d.form for d in drops} == {"para"}
    assert apply_form_drops(tables, drops) == (1, 1)
    kept = {(lemma.text, lemma.language) for lemma in tables.lemmas}
    assert ("para", "pt") not in kept
    assert {("para o leste", "pt"), ("casa", "pt"), ("in", "en")} <= kept


def test_lists_hold_function_words_not_content_homographs() -> None:
    assert {"com", "para", "como", "dela"} <= CLOSED_CLASS["pt"]
    assert "caso" not in CLOSED_CLASS["pt"]
    assert "bajo" not in CLOSED_CLASS["es"]
    assert {"son", "ton", "or"}.isdisjoint(CLOSED_CLASS["fr"])
    assert "en" not in CLOSED_CLASS


def test_the_build_drops_them_and_records_it(tmp_path: Path) -> None:
    summary = build_initial(["en", "pt"], data_fol=tmp_path, omw_entries=_entries())
    store = LexiconStore.from_data_fol(tmp_path)
    assert store.get_lemma_by_id(lemma_id("para", "pt")) is None
    assert store.get_lemma_by_id(lemma_id("casa", "pt")) is not None
    assert summary.counts["lemmas"] == len(store.get_lemmas_by_language("pt")) + len(
        store.get_lemmas_by_language("en")
    )
