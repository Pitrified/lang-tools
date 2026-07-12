"""Tests for the propose -> review -> apply loop (`lexicon.maintenance`)."""

from pathlib import Path

import pytest

from lang_tools.lexicon.codec import PROVENANCE_COL
from lang_tools.lexicon.codec import _dump_table
from lang_tools.lexicon.codec import _read_table_rows
from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.lemma import Lemma
from lang_tools.lexicon.lemma_store import CorpusNotFoundError
from lang_tools.lexicon.maintenance import GlossProposal
from lang_tools.lexicon.maintenance import ProposalConceptNotFoundError
from lang_tools.lexicon.maintenance import apply_gloss_proposals
from lang_tools.lexicon.maintenance import read_proposals
from lang_tools.lexicon.maintenance import thin_gloss_worklist
from lang_tools.lexicon.maintenance import write_proposals
from lang_tools.lexicon.relations import ConceptRelation
from lang_tools.lexicon.sense import Sense

C_MIND = "c__mind-noun-cognition__001122334455"
C_PROCESS = "c__process__001122334466"


def _seed_corpus(data_fol: Path, *, with_provenance: bool = True) -> None:
    """Write a tiny corpus with one thin it gloss and its hypernym context.

    The `mind` concept's it gloss equals its sole it member ("attenzione",
    mirroring the real 05.55 worklist row); its en members and hypernym give
    the repair prompt its grounding context.
    """
    attenzione = Lemma(text="attenzione", language="it", part_of_speech="noun")
    mind = Lemma(text="mind", language="en", part_of_speech="noun")
    process = Lemma(text="process", language="en", part_of_speech="noun")
    concepts = [
        Concept(
            id=C_MIND,
            definitions={
                "en": "knowledge and intellectual ability",
                "it": "attenzione",
            },
            lexfile="noun.cognition",
        ),
        Concept(
            id=C_PROCESS,
            definitions={"en": "a sustained phenomenon marked by changes"},
        ),
    ]
    senses = [
        Sense(lemma_id=attenzione.id, concept_id=C_MIND),
        Sense(lemma_id=mind.id, concept_id=C_MIND),
        Sense(lemma_id=process.id, concept_id=C_PROCESS),
    ]
    sources = ["omw", "omw"] if with_provenance else None
    _dump_table("lemmas", [attenzione, mind, process], data_fol=data_fol)
    _dump_table("concepts", concepts, data_fol=data_fol, sources=sources)
    _dump_table("senses", senses, data_fol=data_fol)
    _dump_table("false_friends", [], data_fol=data_fol)
    _dump_table(
        "concept_relations",
        [
            ConceptRelation(
                concept_id_a=C_MIND,
                concept_id_b=C_PROCESS,
                relation_type="hypernym",
            )
        ],
        data_fol=data_fol,
    )


def test_worklist_finds_the_thin_gloss_with_context(tmp_path: Path) -> None:
    _seed_corpus(tmp_path)
    worklist = thin_gloss_worklist(tmp_path)
    assert len(worklist) == 1
    entry = worklist[0]
    assert entry.concept_id == C_MIND
    assert entry.language == "it"
    assert entry.definition == "attenzione"
    assert entry.member == "attenzione"
    assert entry.lexfile == "noun.cognition"
    assert entry.english_definition == "knowledge and intellectual ability"
    assert entry.english_members == ["mind"]
    assert entry.hypernym_definition == "a sustained phenomenon marked by changes"


def test_worklist_missing_corpus_raises(tmp_path: Path) -> None:
    with pytest.raises(CorpusNotFoundError):
        thin_gloss_worklist(tmp_path)


def test_proposals_jsonl_round_trip(tmp_path: Path) -> None:
    proposals = [
        GlossProposal(
            concept_id=C_MIND,
            language="it",
            current_definition="attenzione",
            proposed_definition="la facolta di pensare e comprendere",
            rationale="grounded in the en gloss",
        )
    ]
    path = write_proposals(proposals, tmp_path / "staging" / "gloss.jsonl")
    assert read_proposals(path) == proposals


def test_apply_updates_gloss_and_retags_llm(tmp_path: Path) -> None:
    _seed_corpus(tmp_path)
    proposal = GlossProposal(
        concept_id=C_MIND,
        language="it",
        current_definition="attenzione",
        proposed_definition="la facolta di pensare e comprendere",
        status="accepted",
    )
    assert apply_gloss_proposals([proposal], data_fol=tmp_path) == 1
    rows = {row["id"]: row for row in _read_table_rows("concepts", data_fol=tmp_path)}
    edited = rows[C_MIND]
    assert dict(edited["definitions"])["it"] == "la facolta di pensare e comprendere"
    # The edited row re-tags llm; the untouched row keeps its omw tag.
    assert edited[PROVENANCE_COL] == "llm"
    assert rows[C_PROCESS][PROVENANCE_COL] == "omw"
    # The worklist is now empty: the invariant would read 0.
    assert thin_gloss_worklist(tmp_path) == []


def test_apply_skips_non_accepted(tmp_path: Path) -> None:
    _seed_corpus(tmp_path)
    proposal = GlossProposal(
        concept_id=C_MIND,
        language="it",
        current_definition="attenzione",
        proposed_definition="la facolta di pensare e comprendere",
        status="proposed",
    )
    assert apply_gloss_proposals([proposal], data_fol=tmp_path) == 0
    rows = {row["id"]: row for row in _read_table_rows("concepts", data_fol=tmp_path)}
    assert dict(rows[C_MIND]["definitions"])["it"] == "attenzione"


def test_apply_without_provenance_column_stays_without(tmp_path: Path) -> None:
    # A seed/sample corpus with no source column round-trips without minting one.
    _seed_corpus(tmp_path, with_provenance=False)
    proposal = GlossProposal(
        concept_id=C_MIND,
        language="it",
        current_definition="attenzione",
        proposed_definition="la facolta di pensare e comprendere",
        status="accepted",
    )
    assert apply_gloss_proposals([proposal], data_fol=tmp_path) == 1
    rows = _read_table_rows("concepts", data_fol=tmp_path)
    assert all(PROVENANCE_COL not in row for row in rows)


def test_apply_unknown_concept_raises(tmp_path: Path) -> None:
    _seed_corpus(tmp_path)
    proposal = GlossProposal(
        concept_id="c__ghost__000000000000",
        language="it",
        current_definition="x",
        proposed_definition="y",
        status="accepted",
    )
    with pytest.raises(ProposalConceptNotFoundError):
        apply_gloss_proposals([proposal], data_fol=tmp_path)
