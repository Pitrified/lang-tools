"""Tests for the reviewed sense additions (`ingestion.sense_additions`)."""

from typing import TYPE_CHECKING

from lang_tools.lexicon.concept_id import concept_key
from lang_tools.lexicon.ingestion.pipeline import build_initial
from lang_tools.lexicon.ingestion.sense_additions import SENSE_ADDITIONS_FILE
from lang_tools.lexicon.ingestion.sense_additions import SenseAddition
from lang_tools.lexicon.ingestion.sense_additions import apply_sense_additions
from lang_tools.lexicon.ingestion.sense_additions import load_sense_additions
from lang_tools.lexicon.ingestion.sources.omw import SynsetEntry
from lang_tools.lexicon.ingestion.transform import SOURCE_MANUAL
from lang_tools.lexicon.ingestion.transform import TaggedTables
from lang_tools.lexicon.ingestion.transform import transform
from lang_tools.lexicon.lemma_id import lemma_id
from lang_tools.lexicon.lemma_store import LexiconStore
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import write_jsonl

if TYPE_CHECKING:
    from pathlib import Path

PLURAL = '3rd person plural present of "ser": they are'


def _entries() -> list[SynsetEntry]:
    return [
        SynsetEntry(
            "en",
            "en-1",
            "i1",
            "have the quality of being",
            ("be",),
            pos="v",
            lexfile="verb.stative",
        ),
        SynsetEntry("pt", "pt-1", "i1", None, ("ser",), pos="v"),
        SynsetEntry("en", "en-2", "i2", "not only so, but", ("yea",), pos="r"),
        SynsetEntry("pt", "pt-2", "i2", None, ("sim",), pos="r"),
        SynsetEntry("en", "en-3", "i3", "an affirmative", ("yes",), pos="n"),
    ]


def _key(tables: TaggedTables, en_word: str) -> str:
    """Return the concept key of the concept an en lemma is linked to."""
    en = lemma_id(en_word, "en")
    return next(concept_key(s.concept_id) for s in tables.senses if s.lemma_id == en)


def _row(
    word: str, key: str, *, add: bool = True, form_note: str = ""
) -> SenseAddition:
    return SenseAddition(
        lemma_id=lemma_id(word, "pt"),
        concept_key=key,
        word=word,
        language="pt",
        add=add,
        form_note=form_note,
        status="accepted",
    )


def test_an_addition_links_an_existing_lemma_and_creates_a_missing_one() -> None:
    tables = transform(_entries())
    rows = [
        _row("sim", _key(tables, "yes")),
        _row("são", _key(tables, "be"), form_note=PLURAL),
    ]
    assert apply_sense_additions(tables, rows) == (2, 1, 0)
    sao = next(lemma for lemma in tables.lemmas if lemma.text == "são")
    assert sao.part_of_speech == "verb"
    assert tables.lemma_sources[tables.lemmas.index(sao)] == SOURCE_MANUAL
    added = [s for s in tables.senses if s.lemma_id == sao.id]
    assert [s.form_note for s in added] == [PLURAL]
    assert tables.sense_sources[tables.senses.index(added[0])] == SOURCE_MANUAL
    assert len(tables.senses) == len(tables.sense_sources)


def test_an_existing_link_only_takes_the_form_note() -> None:
    tables = transform(_entries())
    senses = len(tables.senses)
    rows = [_row("ser", _key(tables, "be"), form_note="the infinitive")]
    assert apply_sense_additions(tables, rows) == (0, 0, 0)
    assert len(tables.senses) == senses
    ser = lemma_id("ser", "pt")
    assert [s.form_note for s in tables.senses if s.lemma_id == ser] == [
        "the infinitive"
    ]


def test_unknown_concepts_and_mistyped_words_are_stale() -> None:
    tables = transform(_entries())
    mistyped = _row("sao", _key(tables, "be")).model_copy(
        update={"lemma_id": lemma_id("são", "pt")}
    )
    assert apply_sense_additions(tables, [_row("sim", "0123456789ab"), mistyped]) == (
        0,
        0,
        2,
    )


def test_latest_accepted_row_per_link_wins(tmp_path: Path) -> None:
    rows = [
        _row("sim", "0011aabbccdd"),
        _row("vinte", "0022bbccddee"),
        # a later add: false row retracts vinte's link
        _row("vinte", "0022bbccddee", add=False),
        _row("seis", "0033ccddeeff").model_copy(update={"status": "proposed"}),
    ]
    write_jsonl(rows, curated_path(tmp_path, SENSE_ADDITIONS_FILE))
    loaded = {(row.word, row.add) for row in load_sense_additions(tmp_path)}
    assert loaded == {("sim", True), ("vinte", False)}
    tables = transform(_entries())
    assert apply_sense_additions(tables, load_sense_additions(tmp_path))[0] == 0


def test_the_build_brings_the_lemma_back_with_its_form_note(tmp_path: Path) -> None:
    tables = transform(_entries())
    rows = [_row("são", _key(tables, "be"), form_note=PLURAL)]
    write_jsonl(rows, curated_path(tmp_path, SENSE_ADDITIONS_FILE))
    build_initial(["en", "pt"], data_fol=tmp_path, omw_entries=_entries())
    store = LexiconStore.from_data_fol(tmp_path)
    card = store.lemma_card(lemma_id("são", "pt"))
    assert card is not None
    assert card.form_note == PLURAL
    assert card.translations["en"] == ["be"]
    assert card.sense_frequency is not None
    ser_card = store.lemma_card(lemma_id("ser", "pt"))
    assert ser_card is not None
    assert ser_card.form_note is None
