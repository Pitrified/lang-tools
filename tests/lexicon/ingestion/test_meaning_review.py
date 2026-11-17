"""Tests for the meaning review: worklists, hints, labels, batches, curated rows."""

from typing import TYPE_CHECKING

import pytest

from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.concept_id import concept_key
from lang_tools.lexicon.ingestion.form_review import MEMBER_FORM_DROPS_FILE
from lang_tools.lexicon.ingestion.form_review import FormDrop
from lang_tools.lexicon.ingestion.lead_translations import LEAD_TRANSLATIONS_FILE
from lang_tools.lexicon.ingestion.lead_translations import LeadTranslation
from lang_tools.lexicon.ingestion.meaning_review import LEAD_PREFIX
from lang_tools.lexicon.ingestion.meaning_review import MEMBER_PREFIX
from lang_tools.lexicon.ingestion.meaning_review import REVIEW_LOG_FILE
from lang_tools.lexicon.ingestion.meaning_review import LeadItem
from lang_tools.lexicon.ingestion.meaning_review import MeaningItem
from lang_tools.lexicon.ingestion.meaning_review import MeaningLogRow
from lang_tools.lexicon.ingestion.meaning_review import UnknownBatchKindError
from lang_tools.lexicon.ingestion.meaning_review import apply_batch
from lang_tools.lexicon.ingestion.meaning_review import build_lead_worklist
from lang_tools.lexicon.ingestion.meaning_review import build_member_worklist
from lang_tools.lexicon.ingestion.meaning_review import drill_cards
from lang_tools.lexicon.ingestion.meaning_review import form_of
from lang_tools.lexicon.ingestion.meaning_review import is_verb_form
from lang_tools.lexicon.ingestion.meaning_review import render_batch
from lang_tools.lexicon.ingestion.meaning_review import review_status
from lang_tools.lexicon.ingestion.meaning_review import save_worklist
from lang_tools.lexicon.ingestion.meaning_review import serve_batch
from lang_tools.lexicon.ingestion.review_batches import LabelError
from lang_tools.lexicon.ingestion.sense_additions import SENSE_ADDITIONS_FILE
from lang_tools.lexicon.ingestion.sense_additions import SenseAddition
from lang_tools.lexicon.lemma import Lemma
from lang_tools.lexicon.lemma_store import LexiconStore
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import read_jsonl
from lang_tools.lexicon.sense import Sense

if TYPE_CHECKING:
    from pathlib import Path

C_CONDUIT = "c__conduit__0011aabbccdd"
C_CAREER = "c__career__0022bbccddee"
C_ETERNAL = "c__eternal__0033ccddeeff"
C_CALL = "c__call-verb__0044ddeeff00"

CANAL = Lemma(text="canal", language="pt", part_of_speech="noun")
CANAIS = Lemma(text="canais", language="pt", part_of_speech="noun")
CACHIMBO = Lemma(text="cachimbo", language="pt", part_of_speech="noun")
CARREIRA = Lemma(text="carreira", language="pt", part_of_speech="noun")
ETERNO = Lemma(text="eterno", language="pt", part_of_speech="adjective")
ETERNA = Lemma(text="eterna", language="pt", part_of_speech="adjective")
# A rare word: below the card floor, so not a card, but still a word of a meaning.
RARE = Lemma(text="raro", language="pt", part_of_speech="noun")
PIPE = Lemma(text="pipe", language="en", part_of_speech="noun")
CALLING = Lemma(text="calling", language="en", part_of_speech="noun")
CAREER = Lemma(text="career", language="en", part_of_speech="noun")
CALL = Lemma(text="call", language="en", part_of_speech="verb")
ETERNAL = Lemma(text="eternal", language="en", part_of_speech="adjective")
TUBO = Lemma(text="tubo", language="it", part_of_speech="noun")


def _store() -> LexiconStore:
    def sense(lemma: Lemma, concept: str, zipf: float | None = 4.0) -> Sense:
        return Sense(
            lemma_id=lemma.id,
            concept_id=concept,
            sense_frequency=zipf,
            token_frequency=zipf,
            cefr_level="B1",
        )

    return LexiconStore.from_models(
        lemmas=[
            CANAL,
            CANAIS,
            CACHIMBO,
            CARREIRA,
            ETERNO,
            ETERNA,
            RARE,
            PIPE,
            CALLING,
            CAREER,
            CALL,
            ETERNAL,
            TUBO,
        ],
        concepts=[
            Concept(id=C_CONDUIT, definitions={"en": "a long hollow conduit"}),
            Concept(id=C_CAREER, definitions={"en": "an occupation"}),
            Concept(id=C_ETERNAL, definitions={"en": "lasting forever"}),
            Concept(id=C_CALL, definitions={"en": "utter a cry"}),
        ],
        senses=[
            sense(CANAL, C_CONDUIT),
            sense(CANAIS, C_CONDUIT, 1.0),
            sense(CACHIMBO, C_CONDUIT, 1.0),
            sense(PIPE, C_CONDUIT),
            sense(TUBO, C_CONDUIT),
            sense(CARREIRA, C_CAREER),
            sense(CALLING, C_CAREER, 4.96),
            sense(CAREER, C_CAREER, 4.88),
            sense(CALL, C_CALL, None),
            sense(ETERNO, C_ETERNAL),
            sense(ETERNA, C_ETERNAL, 3.0),
            sense(RARE, C_ETERNAL, 1.0),
            sense(ETERNAL, C_ETERNAL),
        ],
        lookalikes=[],
        concept_relations=[],
        sense_relations=[],
    )


def _worklists(tmp_path: Path) -> LexiconStore:
    store = _store()
    cards = drill_cards(store)
    save_worklist(tmp_path, MEMBER_PREFIX, build_member_worklist(cards))
    save_worklist(tmp_path, LEAD_PREFIX, build_lead_worklist(store, cards))
    return store


def test_drill_cards_keep_the_floor() -> None:
    texts = sorted(card.lemma.text for card in drill_cards(_store()))
    assert texts == ["canal", "carreira", "eterna", "eterno"]


def test_worklists_pick_the_meanings() -> None:
    store = _store()
    cards = drill_cards(store)
    members = build_member_worklist(cards)
    # carreira is the only pt word of its meaning.
    assert sorted(item.concept_id for item in members) == [C_CONDUIT, C_ETERNAL]
    eternal = next(item for item in members if item.concept_id == C_ETERNAL)
    assert eternal.cards == ["eterna", "eterno"]
    leads = build_lead_worklist(store, cards)
    assert [item.concept_id for item in leads] == [C_CAREER]


def test_verb_forms() -> None:
    verbs = {"call", "make", "run", "build"}
    assert is_verb_form("calling", verbs)
    assert is_verb_form("making", verbs)
    assert is_verb_form("running", verbs)
    assert not is_verb_form("ceiling", verbs)
    assert not is_verb_form("calling card", verbs)


def test_form_of_follows_the_rules() -> None:
    assert form_of("canais", "canal", "noun") == 'plural of "canal"'
    assert form_of("eterna", "eterno", "adjective") == 'feminine of "eterno"'
    assert form_of("eternas", "eterno", "adjective") == 'feminine plural of "eterno"'
    assert form_of("cachimbo", "canal", "noun") is None


def test_serve_numbers_words_and_hints(tmp_path: Path) -> None:
    store = _worklists(tmp_path)
    items = serve_batch(tmp_path, store, batch="w0001")
    assert all(isinstance(item, MeaningItem) for item in items)
    words = [
        (word.n, word.text, word.hint)
        for item in items
        if isinstance(item, MeaningItem)
        for word in item.words
    ]
    assert [n for n, _, _ in words] == list(range(1, len(words) + 1))
    hints = {text: hint for _, text, hint in words}
    assert hints["canais"] == 'plural of "canal"'
    assert hints["eterna"] == 'feminine of "eterno"'
    assert hints["cachimbo"] == ""
    text = render_batch(items)
    assert 'canais (B1 noun) [plural of "canal"]' in text
    assert "en: pipe | it: tubo" in text
    # Serving the same id again returns the same batch; another id gets nothing.
    assert serve_batch(tmp_path, store, batch="w0001") == items
    assert serve_batch(tmp_path, store, batch="w0002") == []


def _numbers(items: list) -> dict[str, int]:
    return {word.text: word.n for item in items for word in item.words}


def test_apply_members_writes_forms_drops_and_log(tmp_path: Path) -> None:
    store = _worklists(tmp_path)
    items = serve_batch(tmp_path, store, batch="w0001")
    n = _numbers(items)
    labels = "\n".join(
        [
            f"{n['canal']} k",
            f"{n['canais']} f canal",
            f"{n['cachimbo']} d # a smoking pipe, not a conduit",
            f"{n['eterno']} k",
            f"{n['eterna']} f eterno",
            f"{n['raro']} k",
        ]
    )
    log = apply_batch(tmp_path, "w0001", labels, guide_path=tmp_path / "none.md")
    assert sorted(row.label for row in log) == ["d", "f", "f", "k", "k", "k"]
    forms = read_jsonl(SenseAddition, curated_path(tmp_path, SENSE_ADDITIONS_FILE))
    assert {(row.word, row.form_note) for row in forms} == {
        ("canais", 'plural of "canal"'),
        ("eterna", 'feminine of "eterno"'),
    }
    assert all(row.status == "accepted" and row.add for row in forms)
    drops = read_jsonl(FormDrop, curated_path(tmp_path, MEMBER_FORM_DROPS_FILE))
    assert [(row.form, row.concept_key) for row in drops] == [
        ("cachimbo", concept_key(C_CONDUIT))
    ]
    logged = read_jsonl(MeaningLogRow, curated_path(tmp_path, REVIEW_LOG_FILE))
    assert len(logged) == 6
    status = review_status(tmp_path, MEMBER_PREFIX)
    assert (status.worklist, status.reviewed, status.pending) == (2, 2, [])


def test_apply_lists_every_problem_and_writes_nothing(tmp_path: Path) -> None:
    store = _worklists(tmp_path)
    items = serve_batch(tmp_path, store, batch="w0001")
    n = _numbers(items)
    labels = "\n".join(
        [
            f"{n['canal']} k extra",
            f"{n['canais']} f cachimbo",
            f"{n['cachimbo']} d",
            f"{n['eterno']} f pipe",
            f"{n['eterna']} q",
        ]
    )
    with pytest.raises(LabelError) as error:
        apply_batch(tmp_path, "w0001", labels, guide_path=tmp_path / "none.md")
    assert len(error.value.problems) == 2
    labels = "\n".join(
        [
            f"{n['canal']} k extra",
            f"{n['canais']} f cachimbo",
            f"{n['cachimbo']} d",
            f"{n['eterno']} f pipe",
            f"{n['eterna']} k",
            f"{n['raro']} k",
        ]
    )
    with pytest.raises(LabelError) as error:
        apply_batch(tmp_path, "w0001", labels, guide_path=tmp_path / "none.md")
    assert len(error.value.problems) == 4
    assert not curated_path(tmp_path, REVIEW_LOG_FILE).exists()


def test_apply_leads_writes_the_picked_lead(tmp_path: Path) -> None:
    store = _worklists(tmp_path)
    items = serve_batch(tmp_path, store, batch="l0001")
    assert len(items) == 1
    item = items[0]
    assert isinstance(item, LeadItem)
    assert [option.text for option in item.options] == ["calling", "career"]
    assert render_batch(items).splitlines()[1].strip() == "en: calling | career"
    with pytest.raises(LabelError):
        apply_batch(tmp_path, "l0001", "1 l calling", guide_path=tmp_path / "x.md")
    apply_batch(tmp_path, "l0001", "1 l career", guide_path=tmp_path / "x.md")
    leads = read_jsonl(LeadTranslation, curated_path(tmp_path, LEAD_TRANSLATIONS_FILE))
    assert [(row.word, row.lemma_id, row.card_word) for row in leads] == [
        ("career", CAREER.id, "carreira")
    ]
    status = review_status(tmp_path, LEAD_PREFIX)
    assert (status.reviewed, status.labels) == (1, {"l": 1})


def test_unknown_batch_kind(tmp_path: Path) -> None:
    with pytest.raises(UnknownBatchKindError):
        serve_batch(tmp_path, _store(), batch="u0001")
