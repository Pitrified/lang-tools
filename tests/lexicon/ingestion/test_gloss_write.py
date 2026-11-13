"""Tests for the agent-written pt glosses (`ingestion.gloss_write`)."""

from typing import TYPE_CHECKING

import pytest

from lang_tools.lexicon.ingestion.gloss_write import LOG_FILE
from lang_tools.lexicon.ingestion.gloss_write import WORK_SUBDIR
from lang_tools.lexicon.ingestion.gloss_write import GlossCorrectionError
from lang_tools.lexicon.ingestion.gloss_write import GlossWriteItem
from lang_tools.lexicon.ingestion.gloss_write import apply_batch
from lang_tools.lexicon.ingestion.gloss_write import correct_gloss
from lang_tools.lexicon.ingestion.gloss_write import render_batch
from lang_tools.lexicon.ingestion.gloss_write import serve_batch
from lang_tools.lexicon.ingestion.gloss_write import write_status
from lang_tools.lexicon.ingestion.pipeline import build_initial
from lang_tools.lexicon.ingestion.review_batches import LabelError
from lang_tools.lexicon.ingestion.sources.omw import SynsetEntry
from lang_tools.lexicon.maintenance import GLOSS_BACKFILL_FILE
from lang_tools.lexicon.maintenance import GlossProposal
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import gloss_overrides_path
from lang_tools.lexicon.maintenance import load_gloss_overrides
from lang_tools.lexicon.maintenance import read_jsonl
from lang_tools.lexicon.maintenance import write_jsonl

if TYPE_CHECKING:
    from pathlib import Path

_EXISTING = GlossProposal(
    concept_id="c__other__0011aabbccdd",
    language="es",
    current_definition="",
    proposed_definition="una vivienda",
    status="accepted",
)


def _entries() -> list[SynsetEntry]:
    return [
        SynsetEntry("en", "en-1", "i1", "a dwelling", ("house",), pos="n"),
        SynsetEntry("pt", "pt-1", "i1", None, ("casa",), pos="n"),
        SynsetEntry("en", "en-2", "i2", "a domestic canine", ("dog",), pos="n"),
        SynsetEntry("pt", "pt-2", "i2", None, ("cão",), pos="n"),
        SynsetEntry("en", "en-3", "i3", "a tall woody plant", ("tree",), pos="n"),
        SynsetEntry("pt", "pt-3", "i3", None, ("árvore",), pos="n"),
    ]


@pytest.fixture
def data_fol(tmp_path: Path) -> Path:
    build_initial(["en", "pt"], data_fol=tmp_path, omw_entries=_entries())
    write_jsonl([_EXISTING], curated_path(tmp_path, GLOSS_BACKFILL_FILE))
    return tmp_path


def _rules(tmp_path: Path) -> Path:
    path = tmp_path / "rules.jinja"
    path.write_text("Write the gloss.")
    return path


def _glosses(items: list[GlossWriteItem]) -> str:
    text = {
        "a dwelling": "habitação onde se mora",
        "a domestic canine": "canino doméstico",
        "a tall woody plant": "planta lenhosa alta",
    }
    return "\n".join(f"{item.n}\t{text[item.english_definition]}" for item in items)


def test_serve_reserves_disjoint_batches_and_repeats_a_pending_one(
    data_fol: Path,
) -> None:
    first = serve_batch(data_fol, batch="g0001", size=2)
    second = serve_batch(data_fol, batch="g0002", size=2)
    assert [item.n for item in first] == [1, 2]
    assert len(second) == 1
    assert {item.key for item in first}.isdisjoint(item.key for item in second)
    assert serve_batch(data_fol, batch="g0001", size=2) == first
    assert serve_batch(data_fol, batch="g0003") == []
    assert render_batch(second).count(" | ") == 3


def test_apply_appends_proposed_rows_and_keeps_the_existing_ones(
    data_fol: Path,
) -> None:
    items = serve_batch(data_fol, batch="g0001")
    log = apply_batch(data_fol, "g0001", _glosses(items), rules_path=_rules(data_fol))
    rows = read_jsonl(GlossProposal, curated_path(data_fol, GLOSS_BACKFILL_FILE))
    assert rows[0] == _EXISTING
    assert [row.status for row in rows[1:]] == ["proposed"] * 3
    assert {row.language for row in rows[1:]} == {"pt"}
    assert log.items == 3
    assert log.rules_sha
    assert sorted(log.keys) == sorted(item.key for item in items)
    assert not (data_fol / WORK_SUBDIR / "g0001.jsonl").exists()
    # Written keys reach the corpus only at a rebuild; the log keeps them out.
    assert serve_batch(data_fol, batch="g0002") == []
    status = write_status(data_fol)
    assert (status.left, status.batches, status.written) == (0, 1, 3)
    with pytest.raises(ValueError, match="already applied"):
        serve_batch(data_fol, batch="g0001")


def test_apply_refuses_every_problem_and_writes_nothing(data_fol: Path) -> None:
    items = serve_batch(data_fol, batch="g0001")
    by_text = {item.english_definition: item.n for item in items}
    house, dog, tree = (
        by_text["a dwelling"],
        by_text["a domestic canine"],
        by_text["a tall woody plant"],
    )
    text = "\n".join(
        [
            f"{house}\tcasa",
            f"{dog}\ta domestic canine",
            f"{dog}\tcanino doméstico",
            "9\tnada",
            "no number here",
        ],
    )
    with pytest.raises(LabelError) as error:
        apply_batch(data_fol, "g0001", text, rules_path=_rules(data_fol))
    problems = "\n".join(error.value.problems)
    assert "unreadable line" in problems
    assert "9: no such item" in problems
    assert f"{dog}: written twice" in problems
    assert f"{tree}: missing" in problems
    assert f"{house}: restates a member word" in problems
    rows = read_jsonl(GlossProposal, curated_path(data_fol, GLOSS_BACKFILL_FILE))
    assert rows == [_EXISTING]
    assert not curated_path(data_fol, LOG_FILE).exists()
    assert (data_fol / WORK_SUBDIR / "g0001.jsonl").exists()


def test_screen_reports_an_untranslated_gloss(data_fol: Path) -> None:
    items = serve_batch(data_fol, batch="g0001", size=1)
    with pytest.raises(LabelError, match="untranslated"):
        apply_batch(
            data_fol,
            "g0001",
            f"1 {items[0].english_definition}",
            rules_path=_rules(data_fol),
        )


def test_correct_writes_an_accepted_override(data_fol: Path) -> None:
    items = serve_batch(data_fol, batch="g0001")
    apply_batch(data_fol, "g0001", _glosses(items), rules_path=_rules(data_fol))
    dog = next(item for item in items if item.english_definition == "a domestic canine")
    row = correct_gloss(data_fol, dog.key, "cão doméstico, mamífero canino")
    assert row.current_definition == "canino doméstico"
    assert row.concept_id == dog.concept_id
    assert load_gloss_overrides(data_fol) == [row]
    with pytest.raises(GlossCorrectionError):
        correct_gloss(data_fol, "pt:ffffffffffff", "nada")
    assert len(read_jsonl(GlossProposal, gloss_overrides_path(data_fol))) == 1
