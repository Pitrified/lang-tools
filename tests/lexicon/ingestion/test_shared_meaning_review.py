"""Tests for the shared-meaning review: worklist, labels, batches, flags."""

from typing import TYPE_CHECKING

import pytest

from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.ingestion.review_batches import LabelError
from lang_tools.lexicon.ingestion.shared_meaning_review import GOLD_FILE
from lang_tools.lexicon.ingestion.shared_meaning_review import SharedMeaningGold
from lang_tools.lexicon.ingestion.shared_meaning_review import UnknownRecheckWordError
from lang_tools.lexicon.ingestion.shared_meaning_review import apply_batch
from lang_tools.lexicon.ingestion.shared_meaning_review import build_worklist
from lang_tools.lexicon.ingestion.shared_meaning_review import gold_agreement
from lang_tools.lexicon.ingestion.shared_meaning_review import parse_labels
from lang_tools.lexicon.ingestion.shared_meaning_review import recheck_batch
from lang_tools.lexicon.ingestion.shared_meaning_review import render_batch
from lang_tools.lexicon.ingestion.shared_meaning_review import review_status
from lang_tools.lexicon.ingestion.shared_meaning_review import save_worklist
from lang_tools.lexicon.ingestion.shared_meaning_review import serve_batch
from lang_tools.lexicon.ingestion.shared_meanings import SHARED_MEANING_LOG_FILE
from lang_tools.lexicon.ingestion.shared_meanings import SharedMeaningRow
from lang_tools.lexicon.ingestion.shared_meanings import apply_shared_meanings
from lang_tools.lexicon.ingestion.shared_meanings import load_shared_meanings
from lang_tools.lexicon.lemma import Lemma
from lang_tools.lexicon.lemma_store import LexiconStore
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import read_jsonl
from lang_tools.lexicon.maintenance import write_jsonl
from lang_tools.lexicon.relations import LookalikeRelation
from lang_tools.lexicon.sense import Sense

if TYPE_CHECKING:
    from pathlib import Path

C_AFTERNOON = "c__afternoon-day__0011aabbccdd"
C_LATE = "c__late-tardy__0022bbccddee"
C_HOUSE = "c__house-building__0033ccddeeff"

TARDE = Lemma(text="tarde", language="pt", part_of_speech="noun")
CASA_PT = Lemma(text="casa", language="pt", part_of_speech="noun")
TARDI = Lemma(text="tardi", language="it", part_of_speech="adjective")
CASA_IT = Lemma(text="casa", language="it", part_of_speech="noun")
TARDY = Lemma(text="tardy", language="en", part_of_speech="adjective")
AFTERNOON = Lemma(text="afternoon", language="en", part_of_speech="noun")
POMERIGGIO = Lemma(text="pomeriggio", language="it", part_of_speech="noun")
LATE = Lemma(text="late", language="en", part_of_speech="adjective")


def _lookalikes() -> list[LookalikeRelation]:
    return [
        LookalikeRelation(
            lemma_id_a=TARDE.id,
            lemma_id_b=TARDI.id,
            kind="partial",
            explanation_notes={"en": 'pt "tarde" is mostly afternoon, also late'},
        ),
        LookalikeRelation(lemma_id_a=TARDE.id, lemma_id_b=TARDY.id, kind="full"),
        LookalikeRelation(lemma_id_a=CASA_PT.id, lemma_id_b=CASA_IT.id, kind="cognate"),
    ]


def _store() -> LexiconStore:
    """Build pt *tarde* with a partial it and a full en look-alike, and a cognate.

    it *tardi* has a sense; en *tardy* has none, so it shows ``(no sense)``;
    pt *casa* ~ it *casa* is a cognate and stays off the worklist.
    """
    return LexiconStore.from_models(
        lemmas=[
            TARDE,
            CASA_PT,
            TARDI,
            CASA_IT,
            TARDY,
            AFTERNOON,
            POMERIGGIO,
            LATE,
        ],
        concepts=[
            Concept(
                id=C_AFTERNOON,
                definitions={"en": "the part of the day between noon and evening"},
            ),
            Concept(id=C_LATE, definitions={"en": "later than usual or than expected"}),
            Concept(id=C_HOUSE, definitions={"en": "a building to live in"}),
        ],
        senses=[
            Sense(lemma_id=TARDE.id, concept_id=C_AFTERNOON, sense_frequency=5.0),
            Sense(lemma_id=TARDE.id, concept_id=C_LATE, sense_frequency=4.0),
            Sense(lemma_id=CASA_PT.id, concept_id=C_HOUSE, sense_frequency=5.0),
            Sense(lemma_id=TARDI.id, concept_id=C_LATE, sense_frequency=4.0),
            Sense(lemma_id=CASA_IT.id, concept_id=C_HOUSE, sense_frequency=5.0),
            Sense(lemma_id=AFTERNOON.id, concept_id=C_AFTERNOON, sense_frequency=5.0),
            Sense(lemma_id=POMERIGGIO.id, concept_id=C_AFTERNOON, sense_frequency=4.0),
            Sense(lemma_id=LATE.id, concept_id=C_LATE, sense_frequency=5.0),
        ],
        lookalikes=_lookalikes(),
        concept_relations=[],
        sense_relations=[],
    )


def _served(tmp_path: Path, batch: str = "p0001") -> tuple[LexiconStore, list]:
    store = _store()
    save_worklist(tmp_path, build_worklist(store))
    return store, serve_batch(tmp_path, store, batch=batch)


def test_worklist_lists_the_false_friend_pairs_gold_first() -> None:
    store = _store()
    worklist = build_worklist(store)
    # One pt card, so the look-alike's language and text order the pairs; the
    # cognate is never listed.
    assert [
        (item.target_text, item.known_language, item.known_text) for item in worklist
    ] == [
        ("tarde", "en", "tardy"),
        ("tarde", "it", "tardi"),
    ]
    assert [(item.rank, item.kind) for item in worklist] == [
        (0, "full"),
        (1, "partial"),
    ]
    assert [item.sense_frequency for item in worklist] == [5.0, 5.0]
    gold_first = build_worklist(store, gold_pairs=[(TARDE.id, TARDI.id)])
    assert [item.known_text for item in gold_first] == ["tardi", "tardy"]


def test_serve_reserves_and_repeats_a_pending_batch(tmp_path: Path) -> None:
    store, items = _served(tmp_path)
    assert [(item.n, item.known_text) for item in items] == [(1, "tardy"), (2, "tardi")]
    assert serve_batch(tmp_path, store, batch="p0001") == items


def test_two_batches_never_share_a_pair(tmp_path: Path) -> None:
    store = _store()
    save_worklist(tmp_path, build_worklist(store))
    first = serve_batch(tmp_path, store, batch="p0001", size=1)
    second = serve_batch(tmp_path, store, batch="p0002", size=1)
    assert [item.known_text for item in first] == ["tardy"]
    assert [item.known_text for item in second] == ["tardi"]
    assert serve_batch(tmp_path, store, batch="p0003") == []


def test_render_shows_the_pt_senses_and_the_main_meaning(tmp_path: Path) -> None:
    _, items = _served(tmp_path)
    text = render_batch(items)
    assert text.splitlines()[:3] == [
        "1 pt tarde (noun) ~ en tardy (full)",
        "  note: ",
        "  pt senses: 1 the part of the day between noon and evening"
        " [en: afternoon | it: pomeriggio]",
    ]
    assert (
        "\n             2 later than usual or than expected [en: late | it: tardi]"
        in text
    )
    # A look-alike with no sense says so.
    assert "  en tardy mainly means: (no sense)" in text
    assert "2 pt tarde (noun) ~ it tardi (partial)" in text
    assert '  note: pt "tarde" is mostly afternoon, also late' in text
    # The look-alike's own word is left out of its words.
    assert (
        "  it tardi mainly means: later than usual or than expected"
        " [pt: tarde | en: late]"
    ) in text


def test_labels_parse_every_label() -> None:
    text = (
        "# a comment\n1 s # chegar tarde\n2 d\n3 d! # one region\n4 w # mainly third\n"
    )
    labels = parse_labels("p0001", text, {1, 2, 3, 4})
    assert [labels[n].label for n in range(1, 5)] == ["s", "d", "d", "w"]
    assert labels[3].edge_case
    assert labels[3].reason == "one region"
    assert labels[1].reason == "chegar tarde"
    assert not labels[2].edge_case


def test_a_bad_label_set_lists_every_problem_and_writes_nothing(
    tmp_path: Path,
) -> None:
    _served(tmp_path)
    with pytest.raises(LabelError) as error:
        apply_batch(
            tmp_path, "p0001", "1 w\n3 s\n1 x\nnope\n", guide_path=tmp_path / "g"
        )
    assert error.value.problems == [
        "item 1: w needs a reason after #",
        "item 3 is not in the batch",
        "item 1 has no known label in '1 x'",
        "unparseable line 'nope'",
        "missing item(s) 1, 2",
    ]
    assert not curated_path(tmp_path, SHARED_MEANING_LOG_FILE).exists()
    # The batch is still pending, so it can be applied once fixed.
    assert serve_batch(tmp_path, _store(), batch="p0001")


def test_apply_writes_the_rows_and_an_s_row_builds_a_flag(tmp_path: Path) -> None:
    _, items = _served(tmp_path)
    guide = tmp_path / "guide.md"
    guide.write_text("rules")
    rows = apply_batch(
        tmp_path, "p0001", "1 d\n2 s! # chegar tarde\n", guide_path=guide
    )
    assert [(row.known_text, row.label, row.edge_case) for row in rows] == [
        ("tardy", "d", False),
        ("tardi", "s", True),
    ]
    assert [row.kind for row in rows] == ["full", "partial"]
    assert rows[1].reason == "chegar tarde"
    assert all(row.rulebook_sha and row.model for row in rows)
    logged = read_jsonl(
        SharedMeaningRow, curated_path(tmp_path, SHARED_MEANING_LOG_FILE)
    )
    assert logged == rows
    assert [item.target_id for item in items] == [TARDE.id, TARDE.id]
    # The batch is gone, and its id cannot be served again.
    with pytest.raises(FileNotFoundError):
        apply_batch(tmp_path, "p0001", "1 d\n", guide_path=guide)
    with pytest.raises(ValueError, match="already applied"):
        serve_batch(tmp_path, _store(), batch="p0001")
    assert serve_batch(tmp_path, _store(), batch="p0002") == []
    status = review_status(tmp_path)
    assert (status.worklist, status.labelled, status.batches) == (2, 2, 1)
    assert status.labels == {"d": 1, "s": 1}
    assert status.edge_cases == 1
    # The build flags the s pair only.
    edges = _lookalikes()
    assert apply_shared_meanings(edges, load_shared_meanings(tmp_path)) == (1, 0)
    assert [edge.shares_main_meaning for edge in edges] == [True, False, False]


def test_recheck_serves_a_labelled_pair_and_refuses_an_unlabelled_one(
    tmp_path: Path,
) -> None:
    store, _ = _served(tmp_path)
    guide = tmp_path / "none"
    apply_batch(tmp_path, "p0001", "1 d\n2 d\n", guide_path=guide)
    items = recheck_batch(tmp_path, store, batch="p9001", words=["tarde:it:tardi"])
    assert [(item.n, item.known_language, item.known_text) for item in items] == [
        (1, "it", "tardi")
    ]
    with pytest.raises(UnknownRecheckWordError, match="casa:it:casa"):
        recheck_batch(tmp_path, store, batch="p9002", words=["casa:it:casa"])
    # The new label wins.
    apply_batch(tmp_path, "p9001", "1 s\n", guide_path=guide)
    latest = {row.known_text: row.label for row in load_shared_meanings(tmp_path)}
    assert latest == {"tardy": "d", "tardi": "s"}


def test_gold_agreement_counts_a_miss(tmp_path: Path) -> None:
    write_jsonl(
        [
            SharedMeaningGold(
                target_id=TARDE.id,
                target_text="tarde",
                known_id=TARDI.id,
                known_text="tardi",
                known_language="it",
                label="s",
            ),
            SharedMeaningGold(
                target_id=TARDE.id,
                target_text="tarde",
                known_id=TARDY.id,
                known_text="tardy",
                known_language="en",
                label="d",
            ),
            SharedMeaningGold(
                target_id=CASA_PT.id,
                target_text="casa",
                known_id=CASA_IT.id,
                known_text="casa",
                known_language="it",
                label="s",
            ),
        ],
        curated_path(tmp_path, GOLD_FILE),
    )
    _served(tmp_path)
    apply_batch(tmp_path, "p0001", "1 d\n2 d\n", guide_path=tmp_path / "none")
    result = gold_agreement(tmp_path)
    # tardy agrees; tardi's gold is s; casa was never labelled.
    assert (result.labelled, result.agree) == (2, 1)
    assert result.misses == ["pt tarde ~ it tardi: s -> d"]
