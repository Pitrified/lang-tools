"""Tests for slug tier 2 (`ingestion.slug_qualifiers` + `sources.omw` tiers)."""

from typing import TYPE_CHECKING

from lang_tools.lexicon.concept_id import concept_key
from lang_tools.lexicon.concept_id import source_key_hash
from lang_tools.lexicon.ingestion.pipeline import build_initial
from lang_tools.lexicon.ingestion.slug_qualifiers import SLUG_QUALIFIERS_FILE
from lang_tools.lexicon.ingestion.slug_qualifiers import CollisionGroup
from lang_tools.lexicon.ingestion.slug_qualifiers import SlugQualifier
from lang_tools.lexicon.ingestion.slug_qualifiers import base_of
from lang_tools.lexicon.ingestion.slug_qualifiers import check_qualifiers
from lang_tools.lexicon.ingestion.slug_qualifiers import collision_groups
from lang_tools.lexicon.ingestion.slug_qualifiers import load_slug_qualifiers
from lang_tools.lexicon.ingestion.sources.omw import SynsetEntry
from lang_tools.lexicon.ingestion.sources.omw import group_to_records
from lang_tools.lexicon.lemma_store import LexiconStore
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import write_jsonl
from lang_tools.llm.slug_qualifier import KeyedQualifier
from lang_tools.llm.slug_qualifier import QualifierCandidate
from lang_tools.llm.slug_qualifier import SlugQualifierOutput

if TYPE_CHECKING:
    from pathlib import Path


def _group() -> CollisionGroup:
    return CollisionGroup(
        slug="hot-adj-all",
        base="hot",
        concepts=[
            QualifierCandidate(key="a" * 12, gloss="having a high temperature"),
            QualifierCandidate(key="b" * 12, gloss="recently stolen or smuggled"),
            QualifierCandidate(key="c" * 12, gloss="wanted by the police"),
        ],
    )


def _out(**qualifiers: str) -> SlugQualifierOutput:
    return SlugQualifierOutput(
        qualifiers=[
            KeyedQualifier(key=k * 12, qualifier=v) for k, v in qualifiers.items()
        ],
    )


def _status(rows: list[SlugQualifier]) -> dict[str, str]:
    return {row.concept_key[0]: row.reason or "ok" for row in rows}


def test_gloss_words_are_accepted() -> None:
    rows = check_qualifiers(
        _group(),
        _out(a="temperature", b="Stolen, smuggled", c="police"),
    )
    assert _status(rows) == {"a": "ok", "b": "ok", "c": "ok"}
    assert {row.status for row in rows} == {"accepted"}


def test_each_rule_rejects_on_its_own() -> None:
    rows = check_qualifiers(
        _group(),
        _out(a="heat", b="recently stolen or smuggled", c="hot"),
    )
    assert _status(rows) == {
        "a": "word not in gloss",  # "heat" is not in the gloss: invented
        "b": "length",  # four words
        "c": "repeats the base word",
    }


def test_duplicates_within_a_group_are_both_rejected() -> None:
    group = CollisionGroup(
        slug="x",
        base="x",
        concepts=[
            QualifierCandidate(key="a" * 12, gloss="a red thing"),
            QualifierCandidate(key="b" * 12, gloss="another red thing"),
        ],
    )
    rows = check_qualifiers(group, _out(a="red", b="red"))
    assert set(_status(rows).values()) == {"duplicate within group"}


def test_a_missing_qualifier_is_rejected() -> None:
    rows = check_qualifiers(_group(), _out(a="temperature"))
    assert _status(rows)["b"] == "missing"


def test_base_of_drops_the_lexfile_suffix() -> None:
    assert base_of("hot-adj-all", "adj.all") == "hot"
    assert base_of("aaron", "noun.person") == "aaron"


def _hot_entries() -> list[SynsetEntry]:
    return [
        SynsetEntry(
            "en",
            "en-1",
            "i1",
            "having a high temperature",
            ("hot",),
            pos="a",
            lexfile="adj.all",
        ),
        SynsetEntry(
            "en",
            "en-2",
            "i2",
            "recently stolen or smuggled",
            ("hot",),
            pos="a",
            lexfile="adj.all",
        ),
        SynsetEntry(
            "en",
            "en-3",
            "i3",
            "wanted by the police",
            ("hot",),
            pos="a",
            lexfile="adj.all",
        ),
        SynsetEntry(
            "en",
            "en-4",
            "i4",
            "a warm place",
            ("hot",),
            pos="n",
            lexfile="noun.location",
        ),
    ]


def _slugs(grouped) -> set[str]:  # noqa: ANN001 - GroupedRecords
    return {c.id.rsplit("__", 1)[0].removeprefix("c__") for c in grouped.concepts}


def test_tier2_qualifies_only_the_still_colliding_slugs() -> None:
    qualifiers = {
        source_key_hash("ili::i1"): "temperature",
        source_key_hash("ili::i2"): "stolen",
        # i3 has none: it keeps its tier-1 slug; i4 never collided at tier 1.
        source_key_hash("ili::i4"): "ignored",
    }
    grouped = group_to_records(_hot_entries(), slug_qualifiers=qualifiers)
    assert _slugs(grouped) == {
        "hot-temperature",
        "hot-stolen",
        "hot-adj-all",
        "hot-noun-location",
    }
    assert grouped.qualifiers_applied == 2


def test_tier2_falls_back_when_a_qualified_slug_is_taken() -> None:
    # Two groups pick "stolen" for the same base word: neither may have
    # "hot-stolen", so both move to the longer tier1-qualifier form.
    entries = [
        *_hot_entries(),
        SynsetEntry(
            "en",
            "en-5",
            "i5",
            "a stolen place",
            ("hot",),
            pos="n",
            lexfile="noun.location",
        ),
    ]
    qualifiers = {
        source_key_hash("ili::i2"): "stolen",
        source_key_hash("ili::i5"): "stolen",
    }
    grouped = group_to_records(entries, slug_qualifiers=qualifiers)
    assert {"hot-adj-all-stolen", "hot-noun-location-stolen"} <= _slugs(grouped)
    assert len(_slugs(grouped)) == len(grouped.concepts) - 1  # i1/i3 still share


def test_worklist_and_build_round_trip(tmp_path: Path) -> None:
    build_initial(["en"], data_fol=tmp_path, omw_entries=_hot_entries())
    (group,) = collision_groups(tmp_path)
    assert group.slug == "hot-adj-all"
    assert group.base == "hot"
    assert len(group.concepts) == 3

    by_gloss = {c.gloss: c.key for c in group.concepts}
    picks = {
        "having a high temperature": "temperature",
        "recently stolen or smuggled": "smuggled",
        "wanted by the police": "police",
    }
    rows = check_qualifiers(
        group,
        SlugQualifierOutput(
            qualifiers=[
                KeyedQualifier(key=by_gloss[gloss], qualifier=q)
                for gloss, q in picks.items()
            ],
        ),
    )
    write_jsonl(rows, curated_path(tmp_path, SLUG_QUALIFIERS_FILE))
    assert len(load_slug_qualifiers(tmp_path)) == 3

    summary = build_initial(["en"], data_fol=tmp_path, omw_entries=_hot_entries())
    assert summary.slug_qualifiers_applied == 3
    ids = {c.id for c in LexiconStore.from_data_fol(tmp_path).get_all_concepts()}
    assert any(cid.startswith("c__hot-police__") for cid in ids)
    # The keys are the same before and after the re-slug.
    assert {concept_key(cid) for cid in ids} >= set(by_gloss.values())
    assert collision_groups(tmp_path) == []
