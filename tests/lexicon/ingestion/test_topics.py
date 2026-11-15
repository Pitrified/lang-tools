"""Tests for the topic stage (`ingestion.topics`)."""

import json
from pathlib import Path

import pytest

from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.ingestion.topics import TopicTable
from lang_tools.lexicon.ingestion.topics import UnknownTopicError
from lang_tools.lexicon.ingestion.topics import assign_topics
from lang_tools.lexicon.ingestion.topics import load_topic_table
from lang_tools.lexicon.ingestion.topics import topics_path
from lang_tools.lexicon.relations import ConceptRelation

_FOOD = "c__bread__0011aabbccdd"
_TACKLE = "c__tackle__0011aabbccee"
_HAPPY = "c__happy__0011aabbccff"
_DISEASE = "c__disease__0011aabb0001"
_FLU = "c__flu__0011aabb0002"
_FLU_STRAIN = "c__flu-strain__0011aabb0003"
_GONE_ROOT = "c__gone__0011aabb0009"


def _table() -> TopicTable:
    return TopicTable(
        vocabulary=frozenset({"food", "sports", "activities"}),
        by_lexfile={"noun.food": ("food",), "noun.act": ("activities",)},
        by_domain={"football": ("sports",)},
    )


def _medical_table(*roots: str) -> TopicTable:
    return TopicTable(
        vocabulary=frozenset({"food", "medical"}),
        by_lexfile={"noun.food": ("food",)},
        by_domain={},
        by_hypernym=dict.fromkeys(roots, ("medical",)),
        by_gloss_tag={"pathology": ("medical",)},
    )


def _write(data_fol: Path, payload: dict) -> None:
    path = topics_path(data_fol)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_lexfile_and_domain_both_contribute() -> None:
    concepts = [
        Concept(id=_FOOD, lexfile="noun.food"),
        Concept(id=_TACKLE, lexfile="noun.act"),
        Concept(id=_HAPPY, lexfile="adj.all"),  # unmapped on purpose
    ]
    tagged = assign_topics(concepts, _table(), {_TACKLE: {"football", "law"}})
    assert tagged.tagged == 2
    assert concepts[0].topics == ["food"]
    assert concepts[1].topics == ["activities", "sports"]  # law is unmapped
    assert concepts[2].topics == []


def test_hypernym_root_tags_descendants_through_both_edge_types() -> None:
    concepts = [
        Concept(id=_DISEASE, lexfile="noun.state"),
        Concept(id=_FLU, lexfile="noun.state"),
        Concept(id=_FLU_STRAIN, lexfile="noun.state"),
        Concept(id=_FOOD, lexfile="noun.food"),
    ]
    relations = [
        ConceptRelation(
            concept_id_a=_FLU, concept_id_b=_DISEASE, relation_type="hypernym"
        ),
        ConceptRelation(
            concept_id_a=_FLU_STRAIN,
            concept_id_b=_FLU,
            relation_type="instance_hypernym",
        ),
        ConceptRelation(
            concept_id_a=_FOOD, concept_id_b=_HAPPY, relation_type="hypernym"
        ),
    ]
    stats = assign_topics(concepts, _medical_table(_DISEASE), {}, relations)
    assert [c.topics for c in concepts] == [
        ["medical"],
        ["medical"],
        ["medical"],
        ["food"],
    ]
    assert stats.tagged == 4
    assert stats.per_root == {_DISEASE: 3}
    assert stats.stale_roots == 0


def test_hypernym_does_not_walk_other_relations() -> None:
    concepts = [Concept(id=_DISEASE), Concept(id=_FLU)]
    relations = [
        ConceptRelation(
            concept_id_a=_FLU, concept_id_b=_DISEASE, relation_type="similar"
        ),
    ]
    assign_topics(concepts, _medical_table(_DISEASE), {}, relations)
    assert concepts[1].topics == []


def test_gloss_tag_tags_only_a_gloss_that_opens_with_it() -> None:
    concepts = [
        Concept(id=_FLU, definitions={"en": "(pathology) a morbid change"}),
        Concept(id=_HAPPY, definitions={"en": "a (pathology) mentioned later"}),
        Concept(id=_TACKLE, definitions={"en": "(law) a rule"}),
        Concept(id=_FOOD, definitions={"pt": "(pathology) so, mas nao em ingles"}),
    ]
    stats = assign_topics(concepts, _medical_table(), {})
    assert [c.topics for c in concepts] == [["medical"], [], [], []]
    assert stats.tagged == 1


def test_stale_root_is_counted_and_skipped() -> None:
    concepts = [Concept(id=_DISEASE)]
    stats = assign_topics(concepts, _medical_table(_DISEASE, _GONE_ROOT), {})
    assert stats.stale_roots == 1
    assert stats.per_root == {_DISEASE: 1}


def test_hypernym_map_outside_the_vocabulary_is_rejected() -> None:
    with pytest.raises(UnknownTopicError, match="medical"):
        TopicTable(
            vocabulary=frozenset({"food"}),
            by_lexfile={},
            by_domain={},
            by_hypernym={_DISEASE: ("medical",)},
        )


def test_no_table_tags_nothing() -> None:
    concepts = [Concept(id=_FOOD, lexfile="noun.food")]
    assert assign_topics(concepts, None, {}).tagged == 0
    assert concepts[0].topics == []


def test_mapping_outside_the_vocabulary_is_rejected() -> None:
    with pytest.raises(UnknownTopicError, match="kitchen"):
        TopicTable(
            vocabulary=frozenset({"food"}),
            by_lexfile={"noun.food": ("kitchen",)},
            by_domain={},
        )


def test_load_reads_the_curated_file(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "vocabulary": ["food"],
            "lexfile": {"noun.food": ["food"]},
            "domain": {"cooking": ["food"]},
            "hypernym": {_DISEASE: ["food"]},
            "gloss_tag": {"pathology": ["food"]},
        },
    )
    table = load_topic_table(tmp_path)
    assert table is not None
    assert table.by_hypernym == {_DISEASE: ("food",)}
    assert table.topics_for_gloss("(pathology) x") == ("food",)
    assert table.topics_for("noun.food", set()) == ["food"]
    assert table.topics_for(None, {"cooking"}) == ["food"]


def test_load_returns_none_without_the_file(tmp_path: Path) -> None:
    assert load_topic_table(tmp_path) is None


def test_the_committed_table_is_valid() -> None:
    # The shipped curated table must load: every mapping inside its vocabulary.
    repo_data = Path(__file__).resolve().parents[3] / "data"
    if not topics_path(repo_data).exists():
        pytest.skip("curated topic table not checked out (git LFS)")
    table = load_topic_table(repo_data)
    assert table is not None
    assert table.by_lexfile
    assert len(table.by_hypernym) == 14
    assert "pathology" in table.by_gloss_tag
