"""Tests for the Parquet codec seam (`lang_tools.lexicon.codec`)."""

from pathlib import Path

import pyarrow.parquet as pq
import pytest

from lang_tools.lexicon.codec import PROVENANCE_COL
from lang_tools.lexicon.codec import MalformedRecordError
from lang_tools.lexicon.codec import ProvenanceLengthMismatchError
from lang_tools.lexicon.codec import UnknownTableError
from lang_tools.lexicon.codec import _dump_table
from lang_tools.lexicon.codec import _load_table
from lang_tools.lexicon.codec import model_from_row
from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.lemma import Lemma
from lang_tools.lexicon.lemma import LemmaExample
from lang_tools.lexicon.relations import ConceptRelation
from lang_tools.lexicon.relations import FalseFriendRelation
from lang_tools.lexicon.sense import Sense


def _sample_lemma() -> Lemma:
    return Lemma(
        text="banco",
        language="pt",
        part_of_speech="noun",
        topics=["money", "furniture"],
        examples=[LemmaExample(sentence="o banco", translation="the bank")],
        sources=["csv"],
    )


def _sample_concept() -> Concept:
    return Concept(
        id="c__bank-money__0011aabbccdd",
        definitions={"pt": "instituicao financeira", "en": "a financial institution"},
        lexfile="noun.possession",
        examples={"en": ["she went to the bank", "open a bank account"]},
    )


def _other_concept() -> Concept:
    return Concept(
        id="c__river-water__112233445566",
        definitions={"en": "a flow of water"},
    )


def test_lemma_round_trip_with_nested_columns(tmp_path: Path) -> None:
    lemma = _sample_lemma()
    _dump_table("lemmas", [lemma], data_fol=tmp_path)
    [loaded] = _load_table("lemmas", data_fol=tmp_path)
    assert loaded.model_dump() == lemma.model_dump()
    # Nested columns survive intact.
    assert loaded.topics == ["money", "furniture"]
    assert loaded.examples[0].sentence == "o banco"
    assert loaded.examples[0].translation == "the bank"


def test_concept_map_column_round_trips(tmp_path: Path) -> None:
    concept = _sample_concept()
    _dump_table("concepts", [concept], data_fol=tmp_path)
    [loaded] = _load_table("concepts", data_fol=tmp_path)
    assert loaded == concept
    assert loaded.definitions == {
        "pt": "instituicao financeira",
        "en": "a financial institution",
    }
    # The phase-5.5 Step-4 concept-level fields survive too.
    assert loaded.lexfile == "noun.possession"
    assert loaded.examples == {"en": ["she went to the bank", "open a bank account"]}


def test_false_friend_map_and_canonical_order_round_trip(tmp_path: Path) -> None:
    edge = FalseFriendRelation(
        lemma_id_a="zzz",
        lemma_id_b="aaa",
        similarity_score=0.9,
        explanation_notes={"en": "trap"},
    )
    _dump_table("false_friends", [edge], data_fol=tmp_path)
    [loaded] = _load_table("false_friends", data_fol=tmp_path)
    assert loaded == edge
    # Canonical order is enforced by the model on both write and read.
    assert loaded.lemma_id_a == "aaa"
    assert loaded.explanation_notes == {"en": "trap"}


def test_concept_relation_round_trip(tmp_path: Path) -> None:
    rel = ConceptRelation(
        concept_id_a="c__a__000000000000",
        concept_id_b="c__b__000000000000",
        relation_type="hypernym",
    )
    _dump_table("concept_relations", [rel], data_fol=tmp_path)
    [loaded] = _load_table("concept_relations", data_fol=tmp_path)
    assert loaded == rel


def test_dumped_rows_carry_no_computed_or_backref_columns(tmp_path: Path) -> None:
    """The persisted shape is lean: no cosmetic computed, no hydrated back-refs."""
    _dump_table("lemmas", [_sample_lemma()], data_fol=tmp_path)
    [loaded] = _load_table("lemmas", data_fol=tmp_path)
    dumped = loaded.model_dump()
    assert "senses" not in dumped
    assert "concepts" not in dumped
    # `id` is computed and recomputed on load (not taken from the stored column).
    assert loaded.id == _sample_lemma().id


def test_senses_partition_round_trips_per_language(tmp_path: Path) -> None:
    sense = Sense(lemma_id="lem1", concept_id="c__x__0011aabbccdd", cefr_level="A1")
    _dump_table("senses", [sense], data_fol=tmp_path, lang="pt")
    # Reading the whole partitioned table globs every language file.
    [loaded] = _load_table("senses", data_fol=tmp_path)
    assert loaded == sense
    # And reading just that language returns the same.
    [only_pt] = _load_table("senses", data_fol=tmp_path, lang="pt")
    assert only_pt == sense


def test_lemmas_dump_partitions_by_language(tmp_path: Path) -> None:
    pt = Lemma(text="casa", language="pt")
    en = Lemma(text="house", language="en")
    _dump_table("lemmas", [pt, en], data_fol=tmp_path)
    assert (tmp_path / "lexicon" / "lemmas" / "pt.parquet").exists()
    assert (tmp_path / "lexicon" / "lemmas" / "en.parquet").exists()
    [only_en] = _load_table("lemmas", data_fol=tmp_path, lang="en")
    assert only_en.text == "house"


def test_missing_table_loads_empty(tmp_path: Path) -> None:
    assert _load_table("concepts", data_fol=tmp_path) == []
    assert _load_table("senses", data_fol=tmp_path) == []


def test_unknown_table_raises(tmp_path: Path) -> None:
    with pytest.raises(UnknownTableError):
        _load_table("nope", data_fol=tmp_path)


def test_malformed_row_raises(tmp_path: Path) -> None:
    # A concept row with a malformed id fails validation through the model.
    with pytest.raises(MalformedRecordError):
        model_from_row("concepts", {"id": "not-a-valid-id", "definitions": {}})


def test_provenance_column_written_and_dropped_on_load(tmp_path: Path) -> None:
    concepts = [_sample_concept(), _other_concept()]
    _dump_table("concepts", concepts, data_fol=tmp_path, sources=["omw", "kaikki"])
    # The extra column lands in the Parquet file...
    table = pq.read_table(tmp_path / "lexicon" / "concepts.parquet")
    assert table.column(PROVENANCE_COL).to_pylist() == ["omw", "kaikki"]
    # ...but is dropped on model load (never reaches the thin model).
    loaded = _load_table("concepts", data_fol=tmp_path)
    assert loaded == concepts
    assert all(PROVENANCE_COL not in c.model_dump() for c in loaded)


def test_provenance_partitioned_lemmas_keep_tags_per_language(tmp_path: Path) -> None:
    pt = Lemma(text="casa", language="pt")
    en = Lemma(text="house", language="en")
    _dump_table("lemmas", [pt, en], data_fol=tmp_path, sources=["kaikki", "omw"])
    pt_table = pq.read_table(tmp_path / "lexicon" / "lemmas" / "pt.parquet")
    en_table = pq.read_table(tmp_path / "lexicon" / "lemmas" / "en.parquet")
    assert pt_table.column(PROVENANCE_COL).to_pylist() == ["kaikki"]
    assert en_table.column(PROVENANCE_COL).to_pylist() == ["omw"]


def test_provenance_length_mismatch_raises(tmp_path: Path) -> None:
    with pytest.raises(ProvenanceLengthMismatchError):
        _dump_table("concepts", [_sample_concept()], data_fol=tmp_path, sources=[])
