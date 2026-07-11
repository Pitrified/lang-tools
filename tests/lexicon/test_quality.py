"""Tests for the data-quality checks and report renderer (`lexicon.quality`)."""

from datetime import UTC
from datetime import datetime
from pathlib import Path

import pytest

from lang_tools.lexicon.codec import _dump_table
from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.lemma import Lemma
from lang_tools.lexicon.lemma_store import CorpusNotFoundError
from lang_tools.lexicon.quality import CheckResult
from lang_tools.lexicon.quality import QualityReport
from lang_tools.lexicon.quality import render_report
from lang_tools.lexicon.quality import run_quality_checks
from lang_tools.lexicon.quality import write_report
from lang_tools.lexicon.relations import ConceptRelation
from lang_tools.lexicon.sense import Sense

C_HOUSE = "c__house__0011aabbccdd"
C_BUILDING = "c__building__0011aabbccee"


def _seed_corpus(data_fol: Path, *, lemma_sources: list[str] | None = None) -> None:
    """Write a tiny referentially closed corpus.

    2 concepts, 2 lemmas, 2 senses, 1 hypernym edge. The `building` concept's
    en definition equals its lemma (one `definition == lemma` hit).
    """
    sources = lemma_sources if lemma_sources is not None else ["omw"]
    house = Lemma(text="house", language="en", part_of_speech="noun")
    building = Lemma(
        text="building",
        language="en",
        part_of_speech="noun",
        sources=sources,
    )
    _dump_table("lemmas", [house, building], data_fol=data_fol)
    _dump_table(
        "concepts",
        [
            Concept(
                id=C_HOUSE,
                definitions={"en": "a dwelling that serves as living quarters"},
                lexfile="noun.artifact",
                examples={"en": ["he built a house"]},
            ),
            Concept(id=C_BUILDING, definitions={"en": "building"}),
        ],
        data_fol=data_fol,
    )
    _dump_table(
        "senses",
        [
            Sense(lemma_id=house.id, concept_id=C_HOUSE),
            Sense(lemma_id=building.id, concept_id=C_BUILDING),
        ],
        data_fol=data_fol,
    )
    _dump_table("false_friends", [], data_fol=data_fol)
    _dump_table(
        "concept_relations",
        [
            ConceptRelation(
                concept_id_a=C_HOUSE,
                concept_id_b=C_BUILDING,
                relation_type="hypernym",
            )
        ],
        data_fol=data_fol,
    )


def test_run_quality_checks_clean_corpus_passes(tmp_path: Path) -> None:
    _seed_corpus(tmp_path)
    report = run_quality_checks(tmp_path)
    assert report.passed
    by_name = {inv.name: inv for inv in report.invariants}
    assert by_name["kaikki_tagged_rows"].value == 0
    assert by_name["dangling_edges"].value == 0
    assert by_name["lemmas_without_sense"].value == 0
    # The `building` gloss is the bare lemma: counted, but far below baseline.
    assert by_name["definition_equals_lemma"].value == 1
    assert by_name["definition_equals_lemma"].passed


def test_checks_cover_the_step4_fields(tmp_path: Path) -> None:
    _seed_corpus(tmp_path)
    report = run_quality_checks(tmp_path)
    by_name = {res.name: res for res in report.results}
    # lexfile: 2 concepts, 1 with lexfile, 1 distinct value.
    assert by_name["lexfile_coverage"].rows == [[2, 1, 1]]
    # examples: the house concept has one en example.
    assert by_name["concept_example_coverage"].rows == [["en", 1]]
    # relations: one hypernym edge.
    assert by_name["relation_types"].rows == [["hypernym", 1]]


def test_kaikki_invariant_fails_on_tagged_lemma(tmp_path: Path) -> None:
    _seed_corpus(tmp_path, lemma_sources=["omw", "kaikki"])
    report = run_quality_checks(tmp_path)
    by_name = {inv.name: inv for inv in report.invariants}
    assert by_name["kaikki_tagged_rows"].value == 1
    assert not by_name["kaikki_tagged_rows"].passed
    assert not report.passed


def test_definition_equals_lemma_baseline_is_configurable(tmp_path: Path) -> None:
    _seed_corpus(tmp_path)
    report = run_quality_checks(tmp_path, definition_equals_lemma_baseline=0)
    by_name = {inv.name: inv for inv in report.invariants}
    assert not by_name["definition_equals_lemma"].passed


def test_missing_corpus_raises(tmp_path: Path) -> None:
    with pytest.raises(CorpusNotFoundError):
        run_quality_checks(tmp_path)


def test_render_report_leads_with_invariants(tmp_path: Path) -> None:
    _seed_corpus(tmp_path)
    report = run_quality_checks(tmp_path)
    text = render_report(report)
    assert "## Invariants - PASS" in text
    assert text.index("## Invariants") < text.index("## Row counts")
    # Every check section renders.
    for result in report.results:
        assert f"## {result.title}" in text


def test_render_report_escapes_pipes() -> None:
    report = QualityReport(
        corpus="x",
        generated_at=datetime(2026, 7, 11, tzinfo=UTC),
        invariants=[],
        results=[
            CheckResult(
                name="c",
                title="T",
                description="d",
                columns=["v"],
                rows=[["a|b"]],
            )
        ],
    )
    assert "a\\|b" in render_report(report)


def test_write_report_writes_the_file(tmp_path: Path) -> None:
    _seed_corpus(tmp_path)
    report = run_quality_checks(tmp_path)
    out = tmp_path / "sub" / "report.md"
    assert write_report(report, out) == out
    assert out.read_text(encoding="utf-8").startswith("# 05.4 data quality - report")
