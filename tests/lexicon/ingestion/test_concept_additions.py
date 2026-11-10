"""Tests for the reviewed concept additions (`ingestion.concept_additions`)."""

from typing import TYPE_CHECKING

from lang_tools.lexicon.concept_id import concept_key
from lang_tools.lexicon.ingestion.concept_additions import CONCEPT_ADDITIONS_FILE
from lang_tools.lexicon.ingestion.concept_additions import ConceptAddition
from lang_tools.lexicon.ingestion.concept_additions import apply_concept_additions
from lang_tools.lexicon.ingestion.concept_additions import load_concept_additions
from lang_tools.lexicon.ingestion.pipeline import build_initial
from lang_tools.lexicon.ingestion.sense_additions import SENSE_ADDITIONS_FILE
from lang_tools.lexicon.ingestion.sense_additions import SenseAddition
from lang_tools.lexicon.ingestion.sources.omw import SynsetEntry
from lang_tools.lexicon.ingestion.transform import SOURCE_MANUAL
from lang_tools.lexicon.ingestion.transform import transform
from lang_tools.lexicon.lemma_id import lemma_id
from lang_tools.lexicon.lemma_store import LexiconStore
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import write_jsonl

if TYPE_CHECKING:
    from pathlib import Path

CAN = "be able to; have the ability, power or permission to"


def _entries() -> list[SynsetEntry]:
    return [
        SynsetEntry(
            "en",
            "en-1",
            "i1",
            "airtight sealed metal container",
            ("can",),
            pos="n",
            lexfile="noun.artifact",
        ),
        SynsetEntry("pt", "pt-1", "i1", None, ("lata",), pos="n"),
    ]


def _row(
    source_key: str = "manual:can-be-able",
    *,
    slug: str = "can-be-able",
    add: bool = True,
) -> ConceptAddition:
    return ConceptAddition(
        source_key=source_key,
        slug=slug,
        lexfile="verb.stative",
        definition=CAN,
        members=["can", "be able to"],
        add=add,
        status="accepted",
    )


def test_an_addition_creates_the_concept_and_links_its_members() -> None:
    tables = transform(_entries())
    assert apply_concept_additions(tables, [_row()]) == (1, 1, 0)
    key = _row().concept_key
    concept = next(c for c in tables.concepts if concept_key(c.id) == key)
    assert concept.definitions == {"en": CAN}
    assert tables.concept_sources[tables.concepts.index(concept)] == SOURCE_MANUAL
    linked = {s.lemma_id for s in tables.senses if s.concept_id == concept.id}
    assert linked == {lemma_id("can", "en"), lemma_id("be able to", "en")}
    able = next(lemma for lemma in tables.lemmas if lemma.text == "be able to")
    assert able.part_of_speech == "verb"
    assert len(tables.senses) == len(tables.sense_sources)
    assert len(tables.lemmas) == len(tables.lemma_sources)


def test_a_taken_key_or_a_bad_slug_is_stale() -> None:
    tables = transform(_entries())
    concepts = len(tables.concepts)
    bad_slug = _row("manual:other", slug="Can Be")
    # the second row's key is already the first's concept
    assert apply_concept_additions(tables, [_row(), _row(), bad_slug]) == (1, 1, 2)
    assert len(tables.concepts) == concepts + 1


def test_latest_accepted_row_per_key_wins(tmp_path: Path) -> None:
    rows = [
        _row(),
        _row("manual:must"),
        # a later add: false row retracts must
        _row("manual:must", add=False),
        _row("manual:may").model_copy(update={"status": "proposed"}),
    ]
    write_jsonl(rows, curated_path(tmp_path, CONCEPT_ADDITIONS_FILE))
    loaded = {(row.source_key, row.add) for row in load_concept_additions(tmp_path)}
    assert loaded == {("manual:can-be-able", True), ("manual:must", False)}


def test_the_build_links_a_pt_word_to_the_new_concept(tmp_path: Path) -> None:
    write_jsonl([_row()], curated_path(tmp_path, CONCEPT_ADDITIONS_FILE))
    pode = SenseAddition(
        lemma_id=lemma_id("pode", "pt"),
        concept_key=_row().concept_key,
        word="pode",
        language="pt",
        form_note='3rd person singular present of "poder": he/she can',
        status="accepted",
    )
    write_jsonl([pode], curated_path(tmp_path, SENSE_ADDITIONS_FILE))
    build_initial(["en", "pt"], data_fol=tmp_path, omw_entries=_entries())
    store = LexiconStore.from_data_fol(tmp_path)
    card = store.lemma_card(lemma_id("pode", "pt"))
    assert card is not None
    assert card.gloss == CAN
    assert set(card.translations["en"]) == {"can", "be able to"}
