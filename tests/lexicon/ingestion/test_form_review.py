"""Tests for the member-form review (`ingestion.form_review`)."""

from pathlib import Path

from lang_tools.lexicon.concept_id import concept_key
from lang_tools.lexicon.ingestion.form_review import MEMBER_FORM_DROPS_FILE
from lang_tools.lexicon.ingestion.form_review import FormDrop
from lang_tools.lexicon.ingestion.form_review import apply_form_drops
from lang_tools.lexicon.ingestion.form_review import suspicious_forms
from lang_tools.lexicon.ingestion.pipeline import build_initial
from lang_tools.lexicon.ingestion.sources.omw import SynsetEntry
from lang_tools.lexicon.ingestion.transform import transform
from lang_tools.lexicon.lemma_id import lemma_id
from lang_tools.lexicon.lemma_store import LexiconStore
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import write_jsonl

_DEFINITION = "artéria que irriga o coração"


def _entries() -> list[SynsetEntry]:
    return [
        SynsetEntry(
            "en", "en-1", "i1", "an artery of the heart", ("coronary",), pos="n"
        ),
        SynsetEntry("pt", "pt-1", "i1", None, (_DEFINITION, "coronária"), pos="n"),
        SynsetEntry("en", "en-2", "i2", "a national park", ("Yosemite",), pos="n"),
        SynsetEntry(
            "pt", "pt-2", "i2", None, ("Parque Nacional de Yosemite agora",), pos="n"
        ),
    ]


def _drop(data_fol: Path, form: str, *, status: str = "accepted") -> FormDrop:
    tables = transform(_entries())
    lemma = lemma_id(form, "pt")
    cid = next(s.concept_id for s in tables.senses if s.lemma_id == lemma)
    row = FormDrop(
        lemma_id=lemma,
        concept_key=concept_key(cid),
        language="pt",
        form=form,
        kind="definition",
        drop=True,
        status=status,  # pyright: ignore[reportArgumentType]
    )
    write_jsonl([row], curated_path(data_fol, MEMBER_FORM_DROPS_FILE))
    return row


def test_worklist_finds_long_non_english_forms(tmp_path: Path) -> None:
    build_initial(["en", "pt"], data_fol=tmp_path, omw_entries=_entries())
    items = dict(suspicious_forms(tmp_path))
    forms = {item.form for item in items.values()}
    assert forms == {_DEFINITION, "Parque Nacional de Yosemite agora"}
    item = next(i for i in items.values() if i.form == _DEFINITION)
    assert item.english_definition == "an artery of the heart"
    assert item.other_forms == ["coronária"]


def test_an_accepted_drop_removes_the_sense_and_its_orphan_lemma(
    tmp_path: Path,
) -> None:
    row = _drop(tmp_path, _DEFINITION)
    tables = transform(_entries())
    before = len(tables.senses)
    assert apply_form_drops(tables, [row]) == (1, 1)
    assert len(tables.senses) == before - 1
    assert row.lemma_id not in {lemma.id for lemma in tables.lemmas}
    assert len(tables.lemmas) == len(tables.lemma_sources)


def test_a_row_for_a_sense_the_build_lacks_is_ignored() -> None:
    tables = transform(_entries())
    stale = FormDrop(
        lemma_id="0" * 16,
        concept_key="0" * 12,
        language="pt",
        form="gone",
        kind="garbled",
        drop=True,
        status="accepted",
    )
    assert apply_form_drops(tables, [stale]) == (0, 0)


def test_the_build_applies_only_accepted_drops(tmp_path: Path) -> None:
    _drop(tmp_path, _DEFINITION, status="proposed")
    summary = build_initial(["en", "pt"], data_fol=tmp_path, omw_entries=_entries())
    assert summary.member_forms_dropped == 0

    _drop(tmp_path, _DEFINITION)
    summary = build_initial(["en", "pt"], data_fol=tmp_path, omw_entries=_entries())
    assert summary.member_forms_dropped == 1
    texts = {lem.text for lem in LexiconStore.from_data_fol(tmp_path).get_all_lemmas()}
    assert _DEFINITION not in texts
    assert "coronária" in texts
