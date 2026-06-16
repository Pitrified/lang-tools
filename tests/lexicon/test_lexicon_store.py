"""Tests for the lexical store (`lang_tools.lexicon.lemma_store`)."""

import pytest

from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.hydration import NotHydratedError
from lang_tools.lexicon.hydration import SenseNotHydratedError
from lang_tools.lexicon.lemma import Lemma
from lang_tools.lexicon.lemma_store import LexiconStore
from lang_tools.lexicon.lemma_store import LexiconStoreMode
from lang_tools.lexicon.lemma_store import SqliteModeNotImplementedError
from lang_tools.lexicon.relations import ConceptRelation
from lang_tools.lexicon.relations import FalseFriendRelation
from lang_tools.lexicon.sense import Sense

C_BANK = "c__bank-money__0011aabbccdd"
C_BENCH = "c__bench-seat__0022bbccddee"
C_TRAIN = "c__railway-train__0033ccddeeff"


def _build_store(*, hydrate: bool = True) -> LexiconStore:
    """Build a small fixture graph: 'banco' (pt) polysemous; 'bank' (en) cognate."""
    banco = Lemma(text="banco", language="pt")
    bank = Lemma(text="bank", language="en")
    bench = Lemma(text="bench", language="en")
    lemmas = [banco, bank, bench]

    concepts = [
        Concept(id=C_BANK, definitions={"en": "money"}),
        Concept(id=C_BENCH, definitions={"en": "a seat"}),
    ]
    senses = [
        Sense(lemma_id=banco.id, concept_id=C_BANK),
        Sense(lemma_id=banco.id, concept_id=C_BENCH),
        Sense(lemma_id=bank.id, concept_id=C_BANK),
        Sense(lemma_id=bench.id, concept_id=C_BENCH),
    ]
    false_friends = [
        FalseFriendRelation(lemma_id_a=banco.id, lemma_id_b=bank.id),
    ]
    concept_relations = [
        ConceptRelation(
            concept_id_a=C_BANK,
            concept_id_b=C_BENCH,
            relation_type="related",
        ),
        ConceptRelation(
            concept_id_a=C_TRAIN,
            concept_id_b=C_BANK,
            relation_type="hypernym",
        ),
    ]
    return LexiconStore(
        lemmas=lemmas,
        concepts=concepts,
        senses=senses,
        false_friends=false_friends,
        concept_relations=concept_relations,
        hydrate=hydrate,
    )


def _lemma_id(store: LexiconStore, text: str, language: str) -> str:
    return next(
        lem.id
        for lem in store.get_all_lemmas()
        if lem.text == text and lem.language == language
    )


def test_point_lookups() -> None:
    store = _build_store()
    bid = _lemma_id(store, "banco", "pt")
    lemma = store.get_lemma_by_id(bid)
    concept = store.get_concept_by_id(C_BANK)
    assert lemma is not None
    assert concept is not None
    assert lemma.text == "banco"
    assert concept.definitions == {"en": "money"}


def test_sense_adjacency_both_directions() -> None:
    store = _build_store()
    bid = _lemma_id(store, "banco", "pt")
    # banco -> two concepts (polysemy)
    assert {c.id for c in store.concepts_for_lemma(bid)} == {C_BANK, C_BENCH}
    # bank concept <- banco (pt) + bank (en) (synonymy / cognate)
    langs = {lem.language for lem in store.lemmas_for_concept(C_BANK)}
    assert langs == {"pt", "en"}
    assert len(store.senses_for_lemma(bid)) == 2
    assert len(store.senses_for_concept(C_BANK)) == 2


def test_lemmas_for_concept_language_filter() -> None:
    store = _build_store()
    en_only = store.lemmas_for_concept(C_BANK, language="en")
    assert [lem.text for lem in en_only] == ["bank"]


def test_false_friend_symmetry() -> None:
    """One stored edge appears under both endpoints."""
    store = _build_store()
    banco = _lemma_id(store, "banco", "pt")
    bank = _lemma_id(store, "bank", "en")
    from_banco = store.get_false_friends_for_lemma(banco)
    from_bank = store.get_false_friends_for_lemma(bank)
    assert len(from_banco) == 1
    assert len(from_bank) == 1
    assert from_banco[0][0].text == "bank"
    assert from_bank[0][0].text == "banco"


def test_concept_relations_directional_and_symmetric() -> None:
    store = _build_store()
    # C_BANK touches both a symmetric ('related') and a directional ('hypernym') edge.
    all_for_bank = store.concept_relations_for(C_BANK)
    assert len(all_for_bank) == 2
    # The directional hypernym edge is reachable from its target too.
    hyper = store.concept_relations_for(C_BANK, relation_type="hypernym")
    assert len(hyper) == 1
    assert hyper[0].concept_id_a == C_TRAIN
    # And from the source.
    assert len(store.concept_relations_for(C_TRAIN, relation_type="hypernym")) == 1


def test_hydration_resolves_backrefs() -> None:
    store = _build_store()
    bid = _lemma_id(store, "banco", "pt")
    banco = store.get_lemma_by_id(bid)
    assert banco is not None
    # lemma.senses / lemma.concepts populated
    assert len(banco.resolve_senses()) == 2
    assert {c.id for c in banco.resolve_concepts()} == {C_BANK, C_BENCH}
    # sense.lemma / sense.concept populated, shared instances in resident mode
    sense = banco.resolve_senses()[0]
    assert sense.resolve_lemma() is banco
    assert sense.resolve_concept() is store.get_concept_by_id(sense.concept_id)
    # concept.lemmas grouped by language
    bank_concept = store.get_concept_by_id(C_BANK)
    assert bank_concept is not None
    grouped = bank_concept.resolve_lemmas()
    assert {lem.text for lem in grouped["pt"]} == {"banco"}
    assert {lem.text for lem in grouped["en"]} == {"bank"}


def test_hydration_does_not_leak_into_model_dump() -> None:
    store = _build_store()
    bid = _lemma_id(store, "banco", "pt")
    banco = store.get_lemma_by_id(bid)
    assert banco is not None
    dumped = banco.model_dump()
    assert "senses" not in dumped
    assert "concepts" not in dumped


def test_unhydrated_accessors_raise() -> None:
    store = _build_store(hydrate=False)
    bid = _lemma_id(store, "banco", "pt")
    banco = store.get_lemma_by_id(bid)
    assert banco is not None
    with pytest.raises(NotHydratedError):
        banco.resolve_senses()
    sense = Sense(lemma_id="x", concept_id=C_BANK)
    with pytest.raises(SenseNotHydratedError):
        sense.resolve_lemma()


def test_missing_ids_return_empty_or_none() -> None:
    store = _build_store()
    assert store.get_lemma_by_id("missing") is None
    assert store.get_concept_by_id("missing") is None
    assert store.concepts_for_lemma("missing") == []
    assert store.lemmas_for_concept("missing") == []
    assert store.senses_for_lemma("missing") == []
    assert store.get_false_friends_for_lemma("missing") == []
    assert store.concept_relations_for("missing") == []


def test_sqlite_mode_not_implemented() -> None:
    with pytest.raises(SqliteModeNotImplementedError):
        LexiconStore(
            lemmas=[],
            concepts=[],
            senses=[],
            false_friends=[],
            concept_relations=[],
            mode=LexiconStoreMode.SQLITE,
        )
