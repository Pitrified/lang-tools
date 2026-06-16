"""Tests for `lang_tools.lexicon.relations`."""

from pydantic import ValidationError
import pytest

from lang_tools.lexicon.relations import ConceptRelation
from lang_tools.lexicon.relations import FalseFriendRelation


def test_false_friend_relation_canonical_order() -> None:
    high_first = FalseFriendRelation(lemma_id_a="zzz", lemma_id_b="aaa")
    low_first = FalseFriendRelation(lemma_id_a="aaa", lemma_id_b="zzz")
    assert high_first.lemma_id_a == "aaa"
    assert high_first.lemma_id_b == "zzz"
    assert high_first == low_first


def test_false_friend_relation_rejects_self_edge() -> None:
    with pytest.raises(ValidationError, match="cannot connect an entity to itself"):
        FalseFriendRelation(lemma_id_a="aaa", lemma_id_b="aaa")


def test_concept_relation_directional_keeps_order() -> None:
    rel = ConceptRelation(
        concept_id_a="c__zzz__000000000000",
        concept_id_b="c__aaa__000000000000",
        relation_type="hypernym",
    )
    assert rel.concept_id_a == "c__zzz__000000000000"
    assert rel.concept_id_b == "c__aaa__000000000000"


def test_concept_relation_symmetric_canonical_order() -> None:
    rel = ConceptRelation(
        concept_id_a="c__zzz__000000000000",
        concept_id_b="c__aaa__000000000000",
        relation_type="related",
    )
    assert rel.concept_id_a == "c__aaa__000000000000"
    assert rel.concept_id_b == "c__zzz__000000000000"


def test_concept_relation_rejects_self_edge() -> None:
    with pytest.raises(ValidationError, match="cannot connect an entity to itself"):
        ConceptRelation(
            concept_id_a="c__aaa__000000000000",
            concept_id_b="c__aaa__000000000000",
            relation_type="related",
        )
