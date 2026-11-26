"""Tests for the reviewed shared meanings (`ingestion.shared_meanings`)."""

from typing import TYPE_CHECKING
from typing import Literal

from lang_tools.lexicon.ingestion.shared_meanings import SHARED_MEANING_LOG_FILE
from lang_tools.lexicon.ingestion.shared_meanings import SharedMeaningRow
from lang_tools.lexicon.ingestion.shared_meanings import apply_shared_meanings
from lang_tools.lexicon.ingestion.shared_meanings import load_shared_meanings
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import write_jsonl
from lang_tools.lexicon.relations import LookalikeRelation

if TYPE_CHECKING:
    from pathlib import Path


def _row(
    target_id: str, known_id: str, label: Literal["s", "d", "w"]
) -> SharedMeaningRow:
    return SharedMeaningRow(
        batch="t0001",
        target_id=target_id,
        known_id=known_id,
        kind="partial",
        label=label,
    )


def test_latest_row_per_pair_wins(tmp_path: Path) -> None:
    rows = [
        _row("pt_a", "en_a", "s"),
        _row("pt_a", "en_a", "d"),
        _row("pt_b", "en_b", "d"),
        _row("pt_b", "en_b", "s"),
    ]
    write_jsonl(rows, curated_path(tmp_path, SHARED_MEANING_LOG_FILE))
    loaded = {row.pair: row.label for row in load_shared_meanings(tmp_path)}
    assert loaded == {("en_a", "pt_a"): "d", ("en_b", "pt_b"): "s"}


def test_missing_file_loads_nothing(tmp_path: Path) -> None:
    assert load_shared_meanings(tmp_path) == []


def test_s_flags_partial_and_full_edges_and_only_its_own_pair() -> None:
    partial = LookalikeRelation(lemma_id_a="en_a", lemma_id_b="pt_a", kind="partial")
    full = LookalikeRelation(lemma_id_a="en_b", lemma_id_b="pt_b", kind="full")
    other = LookalikeRelation(lemma_id_a="en_c", lemma_id_b="pt_c", kind="partial")
    rows = [_row("pt_a", "en_a", "s"), _row("pt_b", "en_b", "s")]
    assert apply_shared_meanings([partial, full, other], rows) == (2, 0)
    assert [e.shares_main_meaning for e in (partial, full, other)] == [
        True,
        True,
        False,
    ]


def test_d_and_w_rows_flag_nothing() -> None:
    edge = LookalikeRelation(lemma_id_a="en_a", lemma_id_b="pt_a", kind="partial")
    rows = [_row("pt_a", "en_a", "d")]
    assert apply_shared_meanings([edge], rows) == (0, 0)
    assert apply_shared_meanings([edge], [_row("pt_a", "en_a", "w")]) == (0, 0)
    assert not edge.shares_main_meaning


def test_cognate_edge_and_missing_edge_are_stale() -> None:
    cognate = LookalikeRelation(lemma_id_a="en_a", lemma_id_b="pt_a", kind="cognate")
    rows = [_row("pt_a", "en_a", "s"), _row("pt_x", "en_x", "s")]
    assert apply_shared_meanings([cognate], rows) == (0, 2)
    assert not cognate.shares_main_meaning
