"""Tests for the false-friend meaning review: worklist, labels, batches, pins."""

from typing import TYPE_CHECKING

import pytest

from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.concept_id import concept_key
from lang_tools.lexicon.ingestion.best_senses import BEST_SENSES_FILE
from lang_tools.lexicon.ingestion.best_senses import BestSense
from lang_tools.lexicon.ingestion.best_senses import apply_best_senses
from lang_tools.lexicon.ingestion.best_senses import load_best_senses
from lang_tools.lexicon.ingestion.false_friend_meaning_review import GOLD_FILE
from lang_tools.lexicon.ingestion.false_friend_meaning_review import MeaningGold
from lang_tools.lexicon.ingestion.false_friend_meaning_review import (
    UnknownRecheckWordError,
)
from lang_tools.lexicon.ingestion.false_friend_meaning_review import apply_batch
from lang_tools.lexicon.ingestion.false_friend_meaning_review import build_worklist
from lang_tools.lexicon.ingestion.false_friend_meaning_review import gold_agreement
from lang_tools.lexicon.ingestion.false_friend_meaning_review import parse_labels
from lang_tools.lexicon.ingestion.false_friend_meaning_review import recheck_batch
from lang_tools.lexicon.ingestion.false_friend_meaning_review import render_batch
from lang_tools.lexicon.ingestion.false_friend_meaning_review import review_status
from lang_tools.lexicon.ingestion.false_friend_meaning_review import save_worklist
from lang_tools.lexicon.ingestion.false_friend_meaning_review import serve_batch
from lang_tools.lexicon.ingestion.review_batches import LabelError
from lang_tools.lexicon.lemma import Lemma
from lang_tools.lexicon.lemma_store import LexiconStore
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import read_jsonl
from lang_tools.lexicon.maintenance import write_jsonl
from lang_tools.lexicon.relations import LookalikeRelation
from lang_tools.lexicon.sense import Sense

if TYPE_CHECKING:
    from pathlib import Path

C_ANGRY = "c__angry-mad__0011aabbccdd"
C_GOOD = "c__good-fine__0022bbccddee"
C_BRAVE = "c__brave-bold__0033ccddeeff"
C_FINGER = "c__finger-digit__0044ddeeff00"
C_TOE = "c__toe-digit__0055eeff0011"
C_HOUSE = "c__house-building__0066ff001122"
C_FAMILY = "c__house-family__0077001122aa"
C_FINE = "c__exquisite-fine__0088112233bb"
C_WEIRD = "c__weird-odd__0099223344cc"

BRAVO_PT = Lemma(text="bravo", language="pt", part_of_speech="adjective")
DITO_PT = Lemma(text="dito", language="pt", part_of_speech="adjective")
CASA_PT = Lemma(text="casa", language="pt", part_of_speech="noun")
ESQUISITO = Lemma(text="esquisito", language="pt", part_of_speech="adjective")
ESQUISITA = Lemma(text="esquisita", language="pt", part_of_speech="adjective")
BRAVO_IT = Lemma(text="bravo", language="it", part_of_speech="adjective")
DITO_IT = Lemma(text="dito", language="it", part_of_speech="noun")
CASA_IT = Lemma(text="casa", language="it", part_of_speech="noun")
BRAVE = Lemma(text="brave", language="en", part_of_speech="adjective")
EXQUISITE = Lemma(text="exquisite", language="en", part_of_speech="adjective")
GOOD = Lemma(text="good", language="en", part_of_speech="adjective")
FINGER = Lemma(text="finger", language="en", part_of_speech="noun")
TOE = Lemma(text="toe", language="en", part_of_speech="noun")


def _store(senses: list[Sense] | None = None) -> LexiconStore:
    """Build pt cards with it and en false friends of one, two and three senses.

    it *bravo* (good, brave) and it *dito* (toe before finger, on commonness)
    are on the worklist; en *exquisite* is the false friend of two pt words;
    en *brave* has one sense and it *casa* is only a cognate, so both stay out.
    """
    return LexiconStore.from_models(
        lemmas=[
            BRAVO_PT,
            DITO_PT,
            CASA_PT,
            ESQUISITO,
            ESQUISITA,
            BRAVO_IT,
            DITO_IT,
            CASA_IT,
            BRAVE,
            EXQUISITE,
            GOOD,
            FINGER,
            TOE,
        ],
        concepts=[
            Concept(id=C_ANGRY, definitions={"en": "feeling anger"}),
            Concept(
                id=C_GOOD, definitions={"en": "having good qualities"}, commonness=2
            ),
            Concept(id=C_BRAVE, definitions={"en": "having courage"}),
            Concept(id=C_FINGER, definitions={"en": "a digit of the hand"}),
            Concept(id=C_TOE, definitions={"en": "a digit of the foot"}, commonness=2),
            Concept(id=C_HOUSE, definitions={"en": "a building to live in"}),
            Concept(id=C_FAMILY, definitions={"en": "a family line"}),
            Concept(id=C_FINE, definitions={"en": "of rare beauty"}),
            Concept(id=C_WEIRD, definitions={"en": "strange"}),
        ],
        senses=senses if senses is not None else _senses(),
        lookalikes=[
            LookalikeRelation(
                lemma_id_a=BRAVO_PT.id,
                lemma_id_b=BRAVO_IT.id,
                kind="full",
                explanation_notes={"en": 'it "bravo" is mostly good'},
            ),
            LookalikeRelation(
                lemma_id_a=BRAVO_PT.id, lemma_id_b=BRAVE.id, kind="partial"
            ),
            LookalikeRelation(
                lemma_id_a=DITO_PT.id, lemma_id_b=DITO_IT.id, kind="full"
            ),
            LookalikeRelation(
                lemma_id_a=CASA_PT.id, lemma_id_b=CASA_IT.id, kind="cognate"
            ),
            LookalikeRelation(
                lemma_id_a=ESQUISITO.id, lemma_id_b=EXQUISITE.id, kind="full"
            ),
            LookalikeRelation(
                lemma_id_a=ESQUISITA.id, lemma_id_b=EXQUISITE.id, kind="full"
            ),
        ],
        concept_relations=[],
        sense_relations=[],
    )


def _senses() -> list[Sense]:
    return [
        Sense(lemma_id=BRAVO_PT.id, concept_id=C_ANGRY, sense_frequency=4.0),
        Sense(lemma_id=DITO_PT.id, concept_id=C_GOOD, sense_frequency=4.0),
        Sense(lemma_id=CASA_PT.id, concept_id=C_HOUSE, sense_frequency=5.0),
        Sense(lemma_id=ESQUISITO.id, concept_id=C_WEIRD, sense_frequency=3.5),
        Sense(lemma_id=ESQUISITA.id, concept_id=C_WEIRD, sense_frequency=3.0),
        Sense(lemma_id=BRAVO_IT.id, concept_id=C_GOOD, sense_frequency=4.3),
        Sense(lemma_id=BRAVO_IT.id, concept_id=C_BRAVE, sense_frequency=4.3),
        # it senses tie on frequency; commonness puts "toe" first.
        Sense(lemma_id=DITO_IT.id, concept_id=C_TOE, sense_frequency=4.5),
        Sense(lemma_id=DITO_IT.id, concept_id=C_FINGER, sense_frequency=4.5),
        Sense(lemma_id=CASA_IT.id, concept_id=C_HOUSE, sense_frequency=5.0),
        Sense(lemma_id=CASA_IT.id, concept_id=C_FAMILY, sense_frequency=5.0),
        Sense(lemma_id=BRAVE.id, concept_id=C_BRAVE, sense_frequency=4.0),
        Sense(lemma_id=EXQUISITE.id, concept_id=C_FINE, sense_frequency=3.0),
        Sense(lemma_id=EXQUISITE.id, concept_id=C_WEIRD, sense_frequency=1.0),
        Sense(lemma_id=GOOD.id, concept_id=C_GOOD, sense_frequency=6.0),
        Sense(lemma_id=FINGER.id, concept_id=C_FINGER, sense_frequency=5.0),
        Sense(lemma_id=TOE.id, concept_id=C_TOE, sense_frequency=4.0),
    ]


def _served(tmp_path: Path, batch: str = "f0001") -> tuple[LexiconStore, list]:
    store = _store()
    save_worklist(tmp_path, build_worklist(store))
    return store, serve_batch(tmp_path, store, batch=batch)


def test_worklist_takes_false_friends_with_two_senses_once_gold_first() -> None:
    store = _store()
    worklist = build_worklist(store)
    # By card frequency: dito 4.5, bravo 4.3, exquisite 3.0; brave (one sense)
    # and casa (a cognate) stay out, and exquisite is listed once.
    assert [(item.language, item.lemma_text) for item in worklist] == [
        ("it", "dito"),
        ("it", "bravo"),
        ("en", "exquisite"),
    ]
    assert [item.rank for item in worklist] == [0, 1, 2]
    gold_first = build_worklist(store, gold_ids=[EXQUISITE.id])
    assert [item.lemma_text for item in gold_first] == ["exquisite", "dito", "bravo"]


def test_served_items_show_senses_and_the_pt_words(tmp_path: Path) -> None:
    _, items = _served(tmp_path)
    bravo = next(item for item in items if item.lemma_text == "bravo")
    assert [s.concept_key for s in bravo.senses] == [
        concept_key(C_GOOD),
        concept_key(C_BRAVE),
    ]
    # The lemma itself is left out of its own words; other languages stay.
    assert bravo.senses[0].words == {"en": ["good"], "pt": ["dito"]}
    assert [(pt.text, pt.kind) for pt in bravo.false_friend_of] == [("bravo", "full")]
    exquisite = next(item for item in items if item.lemma_text == "exquisite")
    assert sorted(pt.text for pt in exquisite.false_friend_of) == [
        "esquisita",
        "esquisito",
    ]
    text = render_batch(items)
    assert "2 it bravo (adjective)" in text
    assert '  false friend of pt bravo (full): it "bravo" is mostly good' in text


def test_labels_parse_every_label() -> None:
    text = "# a comment\n1 k\n2 p3\n3 p2! # finger\n4 m # a typeface, not listed\n"
    labels = parse_labels("f0001", text, {1: 2, 2: 3, 3: 2, 4: 2})
    assert [(labels[n].label, labels[n].sense) for n in range(1, 5)] == [
        ("k", 1),
        ("p", 3),
        ("p", 2),
        ("m", None),
    ]
    assert labels[3].edge_case
    assert labels[3].reason == "finger"
    assert not labels[1].edge_case


def test_labels_list_every_problem() -> None:
    text = "1 p1\n2 p4\n3 m\n4 x\n5 k\n5 k\n9 k\nnope\n"
    with pytest.raises(LabelError) as error:
        parse_labels("f0001", text, {1: 2, 2: 3, 3: 2, 4: 2, 5: 2, 6: 2})
    assert error.value.problems == [
        "item 1: p1 is not a sense from 2 to 2 (sense 1 is k)",
        "item 2: p4 is not a sense from 2 to 3 (sense 1 is k)",
        "item 3: m needs a reason after #",
        "item 4 has no known label in '4 x'",
        "item 5 is labelled twice",
        "item 9 is not in the batch",
        "unparseable line 'nope'",
        "missing item(s) 1, 2, 3, 4, 6",
    ]


def test_apply_writes_a_log_row_and_a_pin_row_per_lemma(tmp_path: Path) -> None:
    _, items = _served(tmp_path)
    assert [item.lemma_text for item in items] == ["dito", "bravo", "exquisite"]
    guide = tmp_path / "guide.md"
    guide.write_text("rules")
    rows = apply_batch(
        tmp_path, "f0001", "1 p2 # finger\n2 k\n3 m! # not listed\n", guide_path=guide
    )
    assert [(row.label, row.sense, row.concept_key) for row in rows] == [
        ("p", 2, concept_key(C_FINGER)),
        ("k", 1, concept_key(C_GOOD)),
        ("m", None, None),
    ]
    pins = read_jsonl(BestSense, curated_path(tmp_path, BEST_SENSES_FILE))
    # Only a p pins; k and m keep the frequency pick (no concept).
    assert [(pin.lemma_text, pin.language, pin.concept_key) for pin in pins] == [
        ("dito", "it", concept_key(C_FINGER)),
        ("bravo", "it", None),
        ("exquisite", "en", None),
    ]
    assert all(pin.status == "accepted" and pin.batch == "f0001" for pin in pins)
    assert [pin.edge_case for pin in pins] == [False, False, True]
    assert len({pin.prompt_sha for pin in pins}) == 1
    assert pins[0].prompt_sha
    # The batch is gone, and its id cannot be served again.
    with pytest.raises(FileNotFoundError):
        apply_batch(tmp_path, "f0001", "1 k\n", guide_path=guide)
    with pytest.raises(ValueError, match="already applied"):
        serve_batch(tmp_path, _store(), batch="f0001")
    # Every worklist lemma is labelled, so the next batch is empty.
    assert serve_batch(tmp_path, _store(), batch="f0002") == []
    status = review_status(tmp_path)
    assert (status.worklist, status.labelled, status.batches) == (3, 3, 1)
    assert status.labels == {"k": 1, "m": 1, "p": 1}


def test_a_pin_moves_the_card_and_the_false_friend_means(tmp_path: Path) -> None:
    store, _ = _served(tmp_path)
    card = store.lemma_card(DITO_PT.id, known_languages=["en", "it"])
    assert card is not None
    assert card.lookalikes[0].means == {"en": ["toe"]}
    apply_batch(tmp_path, "f0001", "1 p2\n2 k\n3 k\n", guide_path=tmp_path / "none")
    senses = _senses()
    applied, stale = apply_best_senses(senses, load_best_senses(tmp_path))
    assert (applied, stale) == (1, 0)
    pinned = _store(senses)
    own = pinned.lemma_card(DITO_IT.id)
    assert own is not None
    assert own.concept_id == C_FINGER
    card = pinned.lemma_card(DITO_PT.id, known_languages=["en", "it"])
    assert card is not None
    assert card.lookalikes[0].means == {"en": ["finger"]}


def test_recheck_serves_labelled_lemmas_by_language_and_text(tmp_path: Path) -> None:
    store, _ = _served(tmp_path)
    apply_batch(tmp_path, "f0001", "1 k\n2 k\n3 k\n", guide_path=tmp_path / "none")
    items = recheck_batch(tmp_path, store, batch="f9001", words=["it:bravo"])
    assert [(item.n, item.language, item.lemma_text) for item in items] == [
        (1, "it", "bravo")
    ]
    with pytest.raises(UnknownRecheckWordError, match="en:bravo"):
        recheck_batch(tmp_path, store, batch="f9002", words=["en:bravo"])
    # The new label wins.
    apply_batch(tmp_path, "f9001", "1 p2\n", guide_path=tmp_path / "none")
    latest = load_best_senses(tmp_path)
    assert {pin.lemma_text: pin.concept_key for pin in latest}["bravo"] == concept_key(
        C_BRAVE
    )


def test_gold_agreement(tmp_path: Path) -> None:
    write_jsonl(
        [
            MeaningGold(
                lemma_id=DITO_IT.id,
                lemma_text="dito",
                language="it",
                best=[concept_key(C_FINGER)],
            ),
            MeaningGold(
                lemma_id=BRAVO_IT.id, lemma_text="bravo", language="it", best=[]
            ),
            MeaningGold(
                lemma_id=EXQUISITE.id,
                lemma_text="exquisite",
                language="en",
                best=[concept_key(C_FINE)],
            ),
            MeaningGold(lemma_id=GOOD.id, lemma_text="good", language="en", best=[]),
        ],
        curated_path(tmp_path, GOLD_FILE),
    )
    _served(tmp_path)
    apply_batch(tmp_path, "f0001", "1 p2\n2 k\n3 k\n", guide_path=tmp_path / "none")
    result = gold_agreement(tmp_path)
    # dito and exquisite agree; bravo's gold is m, and good was never labelled.
    assert (result.labelled, result.agree) == (3, 2)
    assert result.misses == [f"it bravo: m -> {concept_key(C_GOOD)}"]
