"""Tests for the agent-harness look-alike review: worklist, batches, labels."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

import pytest

from lang_tools.lexicon.ingestion.lookalike_review import LabelError
from lang_tools.lexicon.ingestion.lookalike_review import ReviewLogRow
from lang_tools.lexicon.ingestion.lookalike_review import apply_batch
from lang_tools.lexicon.ingestion.lookalike_review import build_worklist
from lang_tools.lexicon.ingestion.lookalike_review import import_gold
from lang_tools.lexicon.ingestion.lookalike_review import parse_labels
from lang_tools.lexicon.ingestion.lookalike_review import recheck_batch
from lang_tools.lexicon.ingestion.lookalike_review import review_status
from lang_tools.lexicon.ingestion.lookalike_review import serve_batch
from lang_tools.lexicon.ingestion.lookalike_review import tier_of
from lang_tools.lexicon.ingestion.lookalikes import GOLD_FILE
from lang_tools.lexicon.ingestion.lookalikes import LOOKALIKES_FILE
from lang_tools.lexicon.ingestion.lookalikes import REVIEW_MODEL
from lang_tools.lexicon.ingestion.lookalikes import GoldPair
from lang_tools.lexicon.ingestion.lookalikes import LookalikeCandidate
from lang_tools.lexicon.ingestion.lookalikes import LookalikeProposal
from lang_tools.lexicon.ingestion.lookalikes import apply_lookalikes
from lang_tools.lexicon.ingestion.lookalikes import load_lookalikes
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import read_jsonl
from lang_tools.lexicon.maintenance import write_jsonl

if TYPE_CHECKING:
    from pathlib import Path

    from lang_tools.lexicon.lemma_store import LexiconStore


def _cand(
    target: str,
    known: str,
    *,
    kind: str = "full",
    same_key: bool = False,
    form: float = 0.5,
    known_zipf: float = 3.0,
) -> LookalikeCandidate:
    return LookalikeCandidate(
        target_id=target,
        target_text=target,
        known_id=known,
        known_text=known,
        known_language="en",
        similarity=0.8,
        kind=kind,  # type: ignore[arg-type]
        shares_concept=False,
        same_key=same_key,
        form_similarity=form,
        known_zipf=known_zipf,
    )


class _Store:
    """The one store method the batches use: no senses for any lemma."""

    def lemma_sense_cards(self, lemma_id: str) -> list:  # noqa: ARG002 - stub
        return []


def _store() -> LexiconStore:
    return cast("LexiconStore", _Store())


def test_tiers_follow_frequency_and_trap_likeness() -> None:
    assert tier_of(_cand("a", "b"), 5.0) == "A"
    assert tier_of(_cand("a", "b", same_key=True), 3.0) == "B"
    assert tier_of(_cand("a", "b", form=0.9), 2.6) == "B"
    assert tier_of(_cand("a", "b", kind="cognate", same_key=True), 3.0) == "D"
    assert tier_of(_cand("a", "b"), 4.0) == "C"
    assert tier_of(_cand("a", "b"), 3.0) == "D"
    assert tier_of(_cand("a", "b", same_key=True), 1.0) == "E"


def test_worklist_orders_by_tier_then_usefulness() -> None:
    cands = [
        _cand("rare", "x"),
        _cand("common", "y"),
        _cand("trap_lo", "z", same_key=True, known_zipf=2.0),
        _cand("trap_hi", "w", same_key=True, known_zipf=5.0),
        _cand("gold", "g"),
    ]
    zipf = {"rare": 1.0, "common": 5.0, "trap_lo": 3.0, "trap_hi": 2.6, "gold": 5.5}
    items = build_worklist(cands, zipf, skip={"gold:g"})
    assert [i.target_text for i in items] == ["common", "trap_hi", "trap_lo", "rare"]
    assert [i.tier for i in items] == ["A", "B", "B", "E"]
    assert [i.rank for i in items] == [0, 1, 2, 3]


def test_parse_labels_reads_kinds_notes_and_edge_cases() -> None:
    labels = parse_labels(
        "b", '1 c\n# comment\n2 u\n3 f! pt "x" means y\n4 p z', [1, 2, 3, 4]
    )
    assert labels[1].kind == "cognate"
    assert labels[3].kind == "full"
    assert labels[3].edge_case
    assert labels[3].note == 'pt "x" means y'
    assert labels[4].kind == "partial"
    assert not labels[2].note


def test_parse_labels_lists_every_problem() -> None:
    with pytest.raises(LabelError) as error:
        parse_labels("b", "1 c\n1 u\n2 f\n9 c\nhello", [1, 2, 3])
    problems = " | ".join(error.value.problems)
    assert "labelled twice" in problems
    assert "no note" in problems
    assert "not in the batch" in problems
    assert "unparseable" in problems
    assert "missing item(s) 3" in problems


def _setup(data_fol: Path, n: int = 6) -> None:
    cands = [_cand(f"t{i}", f"k{i}") for i in range(n)]
    items = build_worklist(cands, {f"t{i}": 5.0 - i / 10 for i in range(n)})
    write_jsonl(items, curated_path(data_fol, "lookalike_worklist.jsonl"))
    gold = [
        GoldPair(
            pair="pt-en",
            pt=f"g{i}",
            other_language="en",
            other=f"h{i}",
            kind="noise" if i else "full",
            reason="pt: something" if not i else "",
            pt_lemma_id=f"g{i}",
            other_lemma_id=f"h{i}",
        )
        for i in range(3)
    ]
    write_jsonl(gold, curated_path(data_fol, GOLD_FILE))


def _labels_for(items: list, *, gold_right: bool = True) -> str:
    lines = []
    for item in items:
        if item.gold_kind is not None:
            right = "u" if item.gold_kind == "noise" else "f note"
            lines.append(f"{item.n} {right if gold_right else 'c'}")
        else:
            lines.append(f"{item.n} {'f! a note' if item.rank == 0 else 'u'}")
    return "\n".join(lines)


def test_serve_and_apply_a_batch(tmp_path: Path) -> None:
    _setup(tmp_path)
    items = serve_batch(tmp_path, _store(), batch="a0001", size=4, gold_per_batch=2)
    assert len(items) == 6
    assert sum(item.gold_kind is not None for item in items) == 2
    # a second reviewer gets the next items, never the reserved ones
    other = serve_batch(tmp_path, _store(), batch="a0002", size=4, gold_per_batch=0)
    assert {i.key for i in other}.isdisjoint({i.key for i in items})
    assert len(other) == 2
    # serving a pending id again returns it unchanged
    assert serve_batch(tmp_path, _store(), batch="a0001") == items

    log = apply_batch(
        tmp_path, "a0001", _labels_for(items), guide_path=tmp_path / "guide.md"
    )
    assert isinstance(log, ReviewLogRow)
    assert log.items == 4
    assert log.kinds == {"full": 1, "unrelated": 3}
    assert log.gold_agree == 2
    assert log.edge_cases == 1
    assert log.tier == "A"
    rows = read_jsonl(LookalikeProposal, curated_path(tmp_path, LOOKALIKES_FILE))
    assert len(rows) == 4  # gold items only count toward the agreement
    assert {row.model for row in rows} == {REVIEW_MODEL}
    assert {row.status for row in rows if row.kind == "unrelated"} == {"rejected"}
    trap = next(row for row in rows if row.kind == "full")
    assert trap.edge_case
    assert trap.batch == "a0001"
    edges, sources, _ = apply_lookalikes([trap.target_id, trap.known_id], [trap])
    assert len(edges) == 1
    assert sources == ["agent"]

    status = review_status(tmp_path)
    assert status.tiers["A"] == (4, 6)
    assert status.pending == ["a0002"]
    assert (status.gold_agree, status.gold_total) == (2, 2)
    with pytest.raises(ValueError, match="already applied"):
        serve_batch(tmp_path, _store(), batch="a0001")


def test_recheck_serves_reviewed_pairs_until_under_the_current_guide(
    tmp_path: Path,
) -> None:
    _setup(tmp_path)
    old_guide = tmp_path / "old.md"
    old_guide.write_text("old rules")
    items = serve_batch(tmp_path, _store(), batch="a0001", size=4, gold_per_batch=0)
    apply_batch(tmp_path, "a0001", _labels_for(items), guide_path=old_guide)
    keys = [item.key for item in items[:3]]
    guide = tmp_path / "new.md"
    guide.write_text("new rules")

    first = recheck_batch(
        tmp_path,
        _store(),
        batch="r1",
        keys=keys,
        guide_path=guide,
        size=2,
        gold_per_batch=1,
    )
    assert [i.key for i in first if i.gold_kind is None] == keys[:2]
    assert all(i.rank is not None for i in first if i.gold_kind is None)
    # pending keys are not served twice
    second = recheck_batch(
        tmp_path, _store(), batch="r2", keys=keys, guide_path=guide, gold_per_batch=0
    )
    assert [i.key for i in second] == keys[2:]
    labels = "\n".join(
        f"{i.n} u" if i.gold_kind == "noise" else f"{i.n} p a note" for i in first
    )
    apply_batch(tmp_path, "r1", labels, guide_path=guide)
    apply_batch(tmp_path, "r2", "\n".join(f"{i.n} u" for i in second), guide_path=guide)
    # every key now has a row under the new guide, so nothing is left
    assert not recheck_batch(
        tmp_path, _store(), batch="r3", keys=keys, guide_path=guide
    )
    rows = load_lookalikes(tmp_path)
    latest = {f"{r.target_id}:{r.known_id}": r.kind for r in rows}
    # the later row of a pair wins, and a later unrelated row retracts the edge
    assert [latest.get(k) for k in keys] == ["partial", "partial", None]
    edges, _, _ = apply_lookalikes(
        sorted({r.target_id for r in rows} | {r.known_id for r in rows}), rows
    )
    pairs = {frozenset((e.lemma_id_a, e.lemma_id_b)) for e in edges}
    assert {frozenset(k.split(":")) for k in keys[:2]} <= pairs
    assert frozenset(keys[2].split(":")) not in pairs


def test_bad_labels_write_nothing_and_gold_misses_are_logged(tmp_path: Path) -> None:
    _setup(tmp_path)
    items = serve_batch(tmp_path, _store(), batch="b1", size=3, gold_per_batch=2)
    with pytest.raises(LabelError):
        apply_batch(tmp_path, "b1", "1 c", guide_path=tmp_path / "guide.md")
    assert not curated_path(tmp_path, LOOKALIKES_FILE).exists()
    log = apply_batch(
        tmp_path,
        "b1",
        _labels_for(items, gold_right=False),
        guide_path=tmp_path / "guide.md",
    )
    assert log.gold_agree == 0
    assert len(log.gold_misses) == 2


def test_import_gold_is_idempotent(tmp_path: Path) -> None:
    _setup(tmp_path)
    assert import_gold(tmp_path) == 3
    assert import_gold(tmp_path) == 0
    rows = read_jsonl(LookalikeProposal, curated_path(tmp_path, LOOKALIKES_FILE))
    assert {row.model for row in rows} == {"manual"}
    assert sum(row.status == "accepted" for row in rows) == 1
