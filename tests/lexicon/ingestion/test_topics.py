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

_FOOD = "c__bread__0011aabbccdd"
_TACKLE = "c__tackle__0011aabbccee"
_HAPPY = "c__happy__0011aabbccff"


def _table() -> TopicTable:
    return TopicTable(
        vocabulary=frozenset({"food", "sports", "activities"}),
        by_lexfile={"noun.food": ("food",), "noun.act": ("activities",)},
        by_domain={"football": ("sports",)},
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
    assert tagged == 2
    assert concepts[0].topics == ["food"]
    assert concepts[1].topics == ["activities", "sports"]  # law is unmapped
    assert concepts[2].topics == []


def test_no_table_tags_nothing() -> None:
    concepts = [Concept(id=_FOOD, lexfile="noun.food")]
    assert assign_topics(concepts, None, {}) == 0
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
        },
    )
    table = load_topic_table(tmp_path)
    assert table is not None
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
