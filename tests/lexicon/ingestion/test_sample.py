"""Tests for the sample-carving stage (`ingestion.sample`)."""

from lang_tools.lexicon.ingestion.sample import carve_sample
from lang_tools.lexicon.ingestion.sources.omw import SynsetEntry
from lang_tools.lexicon.ingestion.transform import transform
from lang_tools.lexicon.relations import FalseFriendRelation


def _many() -> list[SynsetEntry]:
    return [
        SynsetEntry("en", f"s{i}", f"i{i:03d}", f"def {i}", (f"word{i}",), pos="n")
        for i in range(5)
    ]


def test_carve_keeps_capped_concepts_and_their_lemmas() -> None:
    tables = transform(_many())
    sample = carve_sample(tables, max_concepts=2)
    assert len(sample.concepts) == 2
    kept_concept_ids = {c.id for c in sample.concepts}
    # Every kept sense links a kept concept and a kept lemma.
    kept_lemma_ids = {lem.id for lem in sample.lemmas}
    for sense in sample.senses:
        assert sense.concept_id in kept_concept_ids
        assert sense.lemma_id in kept_lemma_ids
    # The slice is closed: no lemma without a sense in the slice.
    used = {s.lemma_id for s in sample.senses}
    assert kept_lemma_ids == used


def test_carve_drops_edges_with_endpoints_outside_slice() -> None:
    tables = transform(_many())
    # Add a false-friend edge between two lemmas; one will fall outside a tiny slice.
    a, b = tables.lemmas[0].id, tables.lemmas[-1].id
    tables.false_friends.append(FalseFriendRelation(lemma_id_a=a, lemma_id_b=b))
    tables.false_friend_sources.append("manual")
    sample = carve_sample(tables, max_concepts=1)
    # Only one concept's lemma survives, so the cross-slice edge is dropped.
    assert sample.false_friends == []


def test_carve_keeps_fully_internal_edges() -> None:
    tables = transform(_many())
    sample_full = carve_sample(tables, max_concepts=5)
    a, b = sorted([tables.lemmas[0].id, tables.lemmas[1].id])
    sample_full.false_friends.append(FalseFriendRelation(lemma_id_a=a, lemma_id_b=b))
    sample_full.false_friend_sources.append("manual")
    kept = carve_sample(sample_full, max_concepts=5)
    assert len(kept.false_friends) == 1
    assert kept.false_friend_sources == ["manual"]


def test_carve_prefers_richer_concepts_over_alphabetical_order() -> None:
    # "aaa" sorts first by id but is monolingual and exampleless; the ranked
    # carve must prefer the multilingual concept with an example (05.59).
    entries = [
        SynsetEntry("en", "s1", "i001", "def aaa", ("aaa",), pos="n"),
        SynsetEntry(
            "en", "s2", "i002", "def zzz", ("zzz",), pos="n",
            examples=("a zzz",),
        ),
        SynsetEntry("pt", "s2p", "i002", "def zzz pt", ("zzzpt",), pos="n"),
    ]
    tables = transform(entries)
    sample = carve_sample(tables, max_concepts=1)
    assert len(sample.concepts) == 1
    assert sample.concepts[0].definitions["en"] == "def zzz"
    # The slice stays closed: both language members come along.
    assert {lem.text for lem in sample.lemmas} == {"zzz", "zzzpt"}


def test_carve_falls_back_to_id_order_when_nothing_is_richer() -> None:
    # All equal on languages and examples, so the id tiebreak decides - no
    # special case needed for a thin build.
    tables = transform(_many())
    sample = carve_sample(tables, max_concepts=2)
    kept = [c.id for c in sample.concepts]
    assert kept == sorted(kept)
    assert kept == sorted(c.id for c in tables.concepts)[:2]
