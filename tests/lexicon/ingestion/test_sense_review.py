"""Tests for the agent-harness card-sense review: labels, batches, rebuild."""

from typing import TYPE_CHECKING

import pytest

from lang_tools.lexicon.concept_id import concept_key
from lang_tools.lexicon.ingestion.best_senses import BEST_SENSES_FILE
from lang_tools.lexicon.ingestion.best_senses import BestSense
from lang_tools.lexicon.ingestion.form_review import MEMBER_FORM_DROPS_FILE
from lang_tools.lexicon.ingestion.form_review import FormDrop
from lang_tools.lexicon.ingestion.pipeline import build_initial
from lang_tools.lexicon.ingestion.review_batches import LabelError
from lang_tools.lexicon.ingestion.sense_additions import SENSE_ADDITIONS_FILE
from lang_tools.lexicon.ingestion.sense_additions import SenseAddition
from lang_tools.lexicon.ingestion.sense_review import DROP_KIND
from lang_tools.lexicon.ingestion.sense_review import GOLD_FILE
from lang_tools.lexicon.ingestion.sense_review import SHADOW_LOG_FILE
from lang_tools.lexicon.ingestion.sense_review import WORKLIST_FILE
from lang_tools.lexicon.ingestion.sense_review import CorrectionError
from lang_tools.lexicon.ingestion.sense_review import SenseGold
from lang_tools.lexicon.ingestion.sense_review import add_sense
from lang_tools.lexicon.ingestion.sense_review import agreement
from lang_tools.lexicon.ingestion.sense_review import apply_batch
from lang_tools.lexicon.ingestion.sense_review import build_worklist
from lang_tools.lexicon.ingestion.sense_review import drop_sense
from lang_tools.lexicon.ingestion.sense_review import find_concepts
from lang_tools.lexicon.ingestion.sense_review import import_gold
from lang_tools.lexicon.ingestion.sense_review import load_gold
from lang_tools.lexicon.ingestion.sense_review import parse_labels
from lang_tools.lexicon.ingestion.sense_review import pin_sense
from lang_tools.lexicon.ingestion.sense_review import recheck_batch
from lang_tools.lexicon.ingestion.sense_review import removed_lemmas
from lang_tools.lexicon.ingestion.sense_review import render_batch
from lang_tools.lexicon.ingestion.sense_review import restore_drops
from lang_tools.lexicon.ingestion.sense_review import review_status
from lang_tools.lexicon.ingestion.sense_review import serve_batch
from lang_tools.lexicon.ingestion.sources.omw import SynsetEntry
from lang_tools.lexicon.lemma_id import lemma_id
from lang_tools.lexicon.lemma_store import LexiconStore
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import read_jsonl
from lang_tools.lexicon.maintenance import write_jsonl

if TYPE_CHECKING:
    from pathlib import Path

ENTRIES = [
    SynsetEntry("en", "en-1", "i001", "a sleeve of a shirt", ("sleeve",), pos="n"),
    SynsetEntry("pt", "pt-1", "i001", None, ("manga",), pos="n"),
    SynsetEntry("en", "en-2", "i002", "a tropical fruit", ("mango",), pos="n"),
    SynsetEntry("pt", "pt-2", "i002", None, ("manga",), pos="n"),
    SynsetEntry("en", "en-3", "i003", "a unit of area", ("are",), pos="n"),
    SynsetEntry("pt", "pt-3", "i003", None, ("seja",), pos="n"),
    SynsetEntry("en", "en-4", "i004", "a building for living", ("house",), pos="n"),
    SynsetEntry("pt", "pt-4", "i004", None, ("casa",), pos="n"),
]
BE = SynsetEntry(
    "en",
    "en-5",
    "i005",
    "have the quality of being",
    ("be",),
    pos="v",
    lexfile="verb.stative",
)
MANGA = lemma_id("manga", "pt")
SEJA = lemma_id("seja", "pt")
CASA = lemma_id("casa", "pt")


def _build(data_fol: Path) -> LexiconStore:
    build_initial(["en", "pt"], data_fol=data_fol, omw_entries=[*ENTRIES, BE])
    return LexiconStore.from_data_fol(data_fol)


def _be_key(store: LexiconStore) -> str:
    card = store.lemma_card(lemma_id("be", "en"))
    assert card is not None
    assert card.concept_id is not None
    return concept_key(card.concept_id)


def test_labels_parse_every_action() -> None:
    text = (
        "# a comment\n"
        "1 k\n"
        "2 p3\n"
        "3 d1,2 wrong links\n"
        "4 p2! d1 never the night\n"
        "5 x a form of ser\n"
    )
    labels = parse_labels("s0001", text, {1: 1, 2: 3, 3: 3, 4: 2, 5: 1})
    assert labels[1].pin is None
    assert not labels[1].drops
    assert labels[2].pin == 3
    assert labels[3].drops == [1, 2]
    assert labels[3].reason == "wrong links"
    assert (labels[4].pin, labels[4].drops, labels[4].edge_case) == (2, [1], True)
    assert labels[5].drop_all


def test_labels_list_every_problem() -> None:
    text = (
        "1 k p2\n2 p4\n3 d1\n4 d1,2 both gone\n5 p1 d1 pinned and dropped\n9 k\noops\n"
    )
    with pytest.raises(LabelError) as caught:
        parse_labels("s0001", text, {1: 2, 2: 3, 3: 2, 4: 2, 5: 2, 6: 1})
    problems = caught.value.problems
    assert "item 1: k and x stand alone" in problems
    assert "item 2: a sense outside 1-3" in problems
    assert "item 3: a drop needs a reason" in problems
    assert "item 4: every sense dropped, use x" in problems
    assert "item 5: sense 1 is both pinned and dropped" in problems
    assert "item 9 is not in the batch" in problems
    assert "unparseable line 'oops'" in problems
    assert "missing item(s) 6" in problems


def test_batch_serves_applies_and_rebuilds(tmp_path: Path) -> None:
    """A pin moves the card, an x drops the lemma, and the gold is scored."""
    store = _build(tmp_path)
    casa_concept = store.lemma_sense_cards(CASA)[0].concept_id
    assert casa_concept is not None
    casa_key = concept_key(casa_concept)
    write_jsonl(
        [SenseGold(lemma_id=CASA, lemma_text="casa", language="pt", best=[casa_key])],
        curated_path(tmp_path, GOLD_FILE),
    )
    worklist = build_worklist(store, "pt", skip=[CASA])
    assert {item.lemma_id for item in worklist} == {MANGA, SEJA}
    write_jsonl(worklist, curated_path(tmp_path, WORKLIST_FILE))

    items = serve_batch(tmp_path, store, batch="s0001", gold_per_batch=1)
    assert len(items) == 3
    assert serve_batch(tmp_path, store, batch="s0001") == items
    assert "manga (noun)" in render_batch(items)
    by_text = {item.lemma_text: item for item in items}
    other = by_text["manga"].senses[1].concept_key
    labels = "\n".join(
        [
            f"{by_text['manga'].n} p2",
            f"{by_text['seja'].n} x a form of ser",
            f"{by_text['casa'].n} k",
        ]
    )
    guide = tmp_path / "guide.md"
    guide.write_text("rules")
    log = apply_batch(tmp_path, "s0001", labels, guide_path=guide)
    assert (log.items, log.pinned, log.dropped_lemmas) == (2, 1, 1)
    assert (log.gold_agree, log.gold_keys) == (1, [CASA])
    with pytest.raises(ValueError, match="already applied"):
        serve_batch(tmp_path, store, batch="s0001")
    assert serve_batch(tmp_path, store, batch="s0002") == []
    status = review_status(tmp_path)
    assert (status.languages, status.batches, status.pending) == ({"pt": (2, 2)}, 1, [])

    drops = read_jsonl(FormDrop, curated_path(tmp_path, MEMBER_FORM_DROPS_FILE))
    assert [(d.lemma_id, d.kind, d.batch) for d in drops] == [
        (SEJA, DROP_KIND, "s0001")
    ]
    pins = read_jsonl(BestSense, curated_path(tmp_path, BEST_SENSES_FILE))
    assert {row.lemma_id: row.concept_key for row in pins} == {
        MANGA: other,
        SEJA: None,
    }

    rebuilt = _build(tmp_path)
    card = rebuilt.lemma_card(MANGA)
    assert card is not None
    assert card.concept_id is not None
    assert concept_key(card.concept_id) == other
    assert rebuilt.get_lemma_by_id(SEJA) is None


def test_gold_miss_is_logged(tmp_path: Path) -> None:
    store = _build(tmp_path)
    write_jsonl(
        [SenseGold(lemma_id=SEJA, lemma_text="seja", language="pt")],
        curated_path(tmp_path, GOLD_FILE),
    )
    write_jsonl(
        build_worklist(store, "pt", skip=[SEJA]), curated_path(tmp_path, WORKLIST_FILE)
    )
    items = serve_batch(tmp_path, store, batch="s0001", size=1, gold_per_batch=1)
    labels = "\n".join(f"{item.n} k" for item in items)
    log = apply_batch(tmp_path, "s0001", labels, guide_path=tmp_path / "none.md")
    assert log.gold_agree == 0
    assert log.gold_misses[0].startswith("seja: no card -> ")


def test_imported_gold_drops_a_wrong_lemma(tmp_path: Path) -> None:
    store = _build(tmp_path)
    write_jsonl(
        [SenseGold(lemma_id=SEJA, lemma_text="seja", language="pt", reason="ser")],
        curated_path(tmp_path, GOLD_FILE),
    )
    assert import_gold(tmp_path, store) == 1
    assert import_gold(tmp_path, store) == 0
    assert _build(tmp_path).get_lemma_by_id(SEJA) is None


def test_restore_retracts_a_drop(tmp_path: Path) -> None:
    """A later drop: false row brings the sense, and its lemma, back."""
    store = _build(tmp_path)
    write_jsonl(
        [SenseGold(lemma_id=SEJA, lemma_text="seja", language="pt", reason="ser")],
        curated_path(tmp_path, GOLD_FILE),
    )
    import_gold(tmp_path, store)
    assert _build(tmp_path).get_lemma_by_id(SEJA) is None
    with pytest.raises(CorrectionError, match="no applied drop"):
        restore_drops(tmp_path, "seja", "pt", reason="x", keys=["000000000000"])
    rows = restore_drops(tmp_path, "seja", "pt", reason="a real noun after all")
    assert [(row.drop, row.batch) for row in rows] == [(False, "correction")]
    assert _build(tmp_path).get_lemma_by_id(SEJA) is not None
    with pytest.raises(CorrectionError, match="no applied drop"):
        restore_drops(tmp_path, "seja", "pt", reason="again")


def test_pin_moves_the_card(tmp_path: Path) -> None:
    store = _build(tmp_path)
    keys = [
        concept_key(card.concept_id)
        for card in store.lemma_sense_cards(MANGA)
        if card.concept_id is not None
    ]
    with pytest.raises(CorrectionError, match="no sense"):
        pin_sense(tmp_path, store, "manga", "pt", "000000000000")
    pin_sense(tmp_path, store, "manga", "pt", keys[1])
    card = _build(tmp_path).lemma_card(MANGA)
    assert card is not None
    assert card.concept_id is not None
    assert concept_key(card.concept_id) == keys[1]


def test_labels_parse_an_addition_and_its_problems() -> None:
    labels = parse_labels(
        "m0001",
        "1 a0123456789ab {plural of ser: they are} the verb is the frequent reading\n"
        "2 d1 a0123456789ab! the right sense is missing\n",
        {1: 1, 2: 2},
    )
    assert labels[1].add == "0123456789ab"
    assert labels[1].form_note == "plural of ser: they are"
    assert labels[1].reason == "the verb is the frequent reading"
    assert labels[1].card([]) == "0123456789ab"
    assert (labels[2].drops, labels[2].add, labels[2].edge_case) == (
        [1],
        "0123456789ab",
        True,
    )
    text = "1 a0123456789ab\n2 a0123456789ab p1 both\n3 k {a note}\n4 p1 why\n"
    with pytest.raises(LabelError) as caught:
        parse_labels("m0001", text, {1: 1, 2: 1, 3: 1, 4: 1}, removed=[4])
    problems = caught.value.problems
    assert "item 1: an addition needs a reason" in problems
    assert "item 2: a pins the added sense, so no p" in problems
    assert "item 3: a form note needs an addition" in problems
    assert "item 4: a removed lemma takes k or a" in problems


def test_a_removed_lemma_comes_back_through_a_recheck(tmp_path: Path) -> None:
    """An x removes seja; a re-check under new rules adds "be" and pins it."""
    store = _build(tmp_path)
    write_jsonl(build_worklist(store, "pt"), curated_path(tmp_path, WORKLIST_FILE))
    items = serve_batch(tmp_path, store, batch="s0001", gold_per_batch=0)
    old = tmp_path / "old.md"
    old.write_text("old rules")
    labels = "\n".join(
        f"{i.n} x a form of ser" if i.lemma_text == "seja" else f"{i.n} k"
        for i in items
    )
    apply_batch(tmp_path, "s0001", labels, guide_path=old)
    store = _build(tmp_path)
    assert removed_lemmas(tmp_path, store, "pt") == [(SEJA, "seja")]
    be = _be_key(store)

    guide = tmp_path / "new.md"
    guide.write_text("new rules")
    served = recheck_batch(
        tmp_path,
        store,
        batch="m0001",
        lemma_ids=[SEJA],
        guide_path=guide,
        gold_per_batch=0,
    )
    assert [(i.lemma_text, i.removed) for i in served] == [("seja", True)]
    assert "seja REMOVED" in render_batch(served)
    assert served[0].senses[0].gloss == "a unit of area"
    with pytest.raises(LabelError, match="no concept"):
        apply_batch(
            tmp_path,
            "m0001",
            "1 a0123456789ab no such key",
            guide_path=guide,
            store=store,
        )
    log = apply_batch(
        tmp_path,
        "m0001",
        f"1 a{be} {{subjunctive of ser}} the verb",
        guide_path=guide,
        store=store,
    )
    assert log.added == 1
    assert log.outcomes[SEJA].add == be
    # every listed lemma is now reviewed under the current rules
    assert not recheck_batch(
        tmp_path, store, batch="m0002", lemma_ids=[SEJA], guide_path=guide
    )
    card = _build(tmp_path).lemma_card(SEJA)
    assert card is not None
    assert card.concept_id is not None
    assert (concept_key(card.concept_id), card.form_note) == (
        be,
        "subjunctive of ser",
    )


def test_a_second_review_writes_no_rows_and_is_compared(tmp_path: Path) -> None:
    store = _build(tmp_path)
    worklist = build_worklist(store, "pt")
    write_jsonl(worklist, curated_path(tmp_path, WORKLIST_FILE))
    ids = [item.lemma_id for item in worklist]
    guide = tmp_path / "guide.md"
    guide.write_text("rules")
    first = recheck_batch(
        tmp_path,
        store,
        batch="m0001",
        lemma_ids=ids,
        guide_path=guide,
        gold_per_batch=0,
    )
    second = recheck_batch(
        tmp_path,
        store,
        batch="n0001",
        lemma_ids=ids,
        guide_path=guide,
        gold_per_batch=0,
        shadow=True,
    )
    assert {i.lemma_id for i in first} == {i.lemma_id for i in second} == set(ids)

    def labels(items: list, seja: str) -> str:
        return "\n".join(
            f"{i.n} {seja}" if i.lemma_text == "seja" else f"{i.n} k" for i in items
        )

    apply_batch(tmp_path, "m0001", labels(first, "x a form of ser"), guide_path=guide)
    pins_before = curated_path(tmp_path, BEST_SENSES_FILE).read_text()
    apply_batch(tmp_path, "n0001", labels(second, "k"), guide_path=guide, shadow=True)
    assert curated_path(tmp_path, BEST_SENSES_FILE).read_text() == pins_before
    assert curated_path(tmp_path, SHADOW_LOG_FILE).exists()
    # the second review is done for these lemmas, whatever their rows
    assert not recheck_batch(
        tmp_path,
        store,
        batch="n0002",
        lemma_ids=ids,
        guide_path=guide,
        shadow=True,
    )
    result = agreement(tmp_path, ["m0001"], ["n0001"])
    assert (result.items, result.first_changed, result.agree_on_changed) == (
        len(ids),
        1,
        0,
    )
    assert result.same_outcome == len(ids) - 1
    assert result.disagreements[0].startswith("seja: card - drop ")
    assert result.disagreements[0].endswith(" -> k")


def test_add_checks_the_concept_and_the_closed_class(tmp_path: Path) -> None:
    store = _build(tmp_path)
    be = _be_key(store)
    with pytest.raises(CorrectionError, match="no concept"):
        add_sense(tmp_path, store, "são", "pt", "0123456789ab", reason="x")
    with pytest.raises(CorrectionError, match="closed-class"):
        add_sense(tmp_path, store, "como", "pt", be, reason="x")
    rows = add_sense(
        tmp_path, store, "são", "pt", be, reason="the verb", form_note="they are"
    )
    assert [type(row).__name__ for row in rows] == ["SenseAddition", "BestSense"]
    added = read_jsonl(SenseAddition, curated_path(tmp_path, SENSE_ADDITIONS_FILE))
    assert [(a.word, a.form_note, a.batch) for a in added] == [
        ("são", "they are", "correction")
    ]
    card = _build(tmp_path).lemma_card(lemma_id("são", "pt"))
    assert card is not None
    assert card.form_note == "they are"


def test_concepts_are_found_by_english_word(tmp_path: Path) -> None:
    store = _build(tmp_path)
    found = find_concepts(store, "house", language="pt")
    assert [(o.gloss, members) for o, members in found] == [
        ("a building for living", ["casa"])
    ]


def test_drop_removes_a_wrong_link(tmp_path: Path) -> None:
    store = _build(tmp_path)
    key = concept_key(store.lemma_sense_cards(SEJA)[0].concept_id or "")
    with pytest.raises(CorrectionError, match="no sense"):
        drop_sense(tmp_path, store, "seja", "pt", "000000000000", reason="x")
    drop_sense(tmp_path, store, "seja", "pt", key, reason="a form of ser")
    assert _build(tmp_path).get_lemma_by_id(SEJA) is None


def test_imported_gold_adds_a_missing_link(tmp_path: Path) -> None:
    store = _build(tmp_path)
    be = _be_key(store)
    write_jsonl(
        [SenseGold(lemma_id=SEJA, lemma_text="seja", language="pt", best=[be])],
        curated_path(tmp_path, GOLD_FILE),
    )
    assert import_gold(tmp_path, store) == 1
    card = _build(tmp_path).lemma_card(SEJA)
    assert card is not None
    assert card.concept_id is not None
    assert concept_key(card.concept_id) == be


def test_a_later_gold_row_replaces_the_answer(tmp_path: Path) -> None:
    write_jsonl(
        [
            SenseGold(lemma_id=SEJA, lemma_text="seja", language="pt"),
            SenseGold(lemma_id=SEJA, lemma_text="seja", language="pt", best=["k1"]),
        ],
        curated_path(tmp_path, GOLD_FILE),
    )
    assert [gold.best for gold in load_gold(tmp_path)] == [["k1"]]
