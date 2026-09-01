"""Tests for the initial-build pipeline (`ingestion.pipeline`).

Drives `build_initial` with in-memory OMW inputs (no network, no ``wn``), then
confirms the source-of-truth Parquet loads back through `LexiconStore` and that
provenance is written on disk but dropped on model load.
"""

from pathlib import Path

import pyarrow.parquet as pq

from lang_tools.lexicon.codec import PROVENANCE_COL
from lang_tools.lexicon.ingestion.acquire import read_manifest
from lang_tools.lexicon.ingestion.pipeline import build_initial
from lang_tools.lexicon.ingestion.sources.omw import SynsetEntry
from lang_tools.lexicon.lemma_store import LexiconStore
from lang_tools.lexicon.maintenance import GlossProposal
from lang_tools.lexicon.maintenance import gloss_overrides_path
from lang_tools.lexicon.maintenance import write_proposals


def _omw() -> list[SynsetEntry]:
    return [
        SynsetEntry("en", "en-1", "i001", "a building for living", ("house",), "n"),
        SynsetEntry("pt", "pt-1", "i001", "uma moradia", ("casa",), "n"),
        SynsetEntry("en", "en-2", "i002", "a flow of water", ("river",), "n"),
        SynsetEntry("pt", "pt-2", "i002", "um curso de agua", ("rio",), "n"),
    ]


def test_build_writes_parquet_manifest_and_loads_via_store(tmp_path: Path) -> None:
    summary = build_initial(["en", "pt"], data_fol=tmp_path, omw_entries=_omw())

    assert summary.counts == {
        "lemmas": 4,
        "concepts": 2,
        "senses": 4,
        "false_friends": 0,
        "concept_relations": 0,
    }

    # The corpus loads back through the SQLite store.
    store = LexiconStore.from_data_fol(tmp_path)
    assert len(store.get_all_lemmas()) == 4
    assert len(store.get_all_concepts()) == 2

    # Cross-lingual grouping: the "house/casa" concept gathers both languages.
    house = next(lem for lem in store.get_all_lemmas() if lem.text == "house")
    concepts = store.concepts_for_lemma(house.id)
    assert len(concepts) == 1
    casa_lemmas = store.lemmas_for_concept(concepts[0].id, language="pt")
    assert {lem.text for lem in casa_lemmas} == {"casa"}
    # Gloss coverage comes from the OMW backbone, per language.
    assert concepts[0].definitions["pt"] == "uma moradia"


def test_manifest_pins_languages_and_counts(tmp_path: Path) -> None:
    build_initial(
        ["en", "pt"],
        data_fol=tmp_path,
        omw_entries=_omw(),
        extra_manifest={"wn_version": "0.9.5", "omw_version": "omw:1.4"},
    )
    manifest = read_manifest(tmp_path)
    assert manifest is not None
    assert manifest["languages"] == ["en", "pt"]
    assert manifest["counts"]["concepts"] == 2
    assert manifest["wn_version"] == "0.9.5"
    assert "built_at" in manifest


def test_provenance_is_omw_only_on_disk_and_dropped_on_load(tmp_path: Path) -> None:
    build_initial(["en", "pt"], data_fol=tmp_path, omw_entries=_omw())
    # The Parquet carries the source column, every row tagged omw (no kaikki).
    table = pq.read_table(tmp_path / "lexicon" / "concepts.parquet")
    assert PROVENANCE_COL in table.column_names
    assert set(table.column(PROVENANCE_COL).to_pylist()) == {"omw"}

    # ...but the loaded model never sees it.
    store = LexiconStore.from_data_fol(tmp_path)
    concept = store.get_all_concepts()[0]
    assert PROVENANCE_COL not in concept.model_dump()


def test_sample_carved_to_separate_corpus(tmp_path: Path) -> None:
    sample_fol = tmp_path / "sample"
    summary = build_initial(
        ["en", "pt"],
        data_fol=tmp_path,
        omw_entries=_omw(),
        sample_data_fol=sample_fol,
        max_sample_concepts=1,
    )
    assert summary.sample_counts["concepts"] == 1
    store = LexiconStore.from_data_fol(sample_fol)
    assert len(store.get_all_concepts()) == 1


def _house_concept_id(data_fol: Path) -> str:
    store = LexiconStore.from_data_fol(data_fol)
    house = next(
        c for c in store.get_all_concepts() if c.definitions.get("pt") == "uma moradia"
    )
    return house.id


def _write_override(
    data_fol: Path,
    concept_id: str,
    *,
    status: str = "accepted",
) -> None:
    write_proposals(
        [
            GlossProposal(
                concept_id=concept_id,
                language="pt",
                current_definition="uma moradia",
                proposed_definition="um edificio onde se vive",
                status=status,  # pyright: ignore[reportArgumentType]
            )
        ],
        gloss_overrides_path(data_fol),
    )


def test_no_override_file_is_a_noop(tmp_path: Path) -> None:
    summary = build_initial(["en", "pt"], data_fol=tmp_path, omw_entries=_omw())
    assert summary.gloss_overrides_applied == 0
    assert summary.gloss_overrides_stale == 0


def test_curated_override_survives_a_rebuild(tmp_path: Path) -> None:
    # Build once to learn the concept id, curate an override, rebuild: the
    # curated gloss must come back on its own (05.58's whole point).
    build_initial(["en", "pt"], data_fol=tmp_path, omw_entries=_omw())
    cid = _house_concept_id(tmp_path)
    _write_override(tmp_path, cid)

    summary = build_initial(["en", "pt"], data_fol=tmp_path, omw_entries=_omw())
    assert summary.gloss_overrides_applied == 1
    assert summary.gloss_overrides_stale == 0

    store = LexiconStore.from_data_fol(tmp_path)
    house = next(c for c in store.get_all_concepts() if c.id == cid)
    assert house.definitions["pt"] == "um edificio onde se vive"
    # ...and only that row is re-tagged llm.
    table = pq.read_table(tmp_path / "lexicon" / "concepts.parquet")
    tags = dict(
        zip(
            table.column("id").to_pylist(),
            table.column(PROVENANCE_COL).to_pylist(),
            strict=True,
        )
    )
    assert tags[cid] == "llm"
    assert set(tags.values()) == {"omw", "llm"}

    manifest = read_manifest(tmp_path)
    assert manifest is not None
    assert manifest["gloss_overrides"] == {"applied": 1, "stale": 0}


def test_unaccepted_override_is_not_applied(tmp_path: Path) -> None:
    build_initial(["en", "pt"], data_fol=tmp_path, omw_entries=_omw())
    cid = _house_concept_id(tmp_path)
    _write_override(tmp_path, cid, status="proposed")

    summary = build_initial(["en", "pt"], data_fol=tmp_path, omw_entries=_omw())
    assert summary.gloss_overrides_applied == 0
    store = LexiconStore.from_data_fol(tmp_path)
    house = next(c for c in store.get_all_concepts() if c.id == cid)
    assert house.definitions["pt"] == "uma moradia"


def test_stale_override_is_counted_not_fatal(tmp_path: Path) -> None:
    # An id no longer in the build (e.g. after a re-slug) must not break the
    # rebuild; it is warned about and counted.
    _write_override(tmp_path, "c__gone__00112233ffff")
    summary = build_initial(["en", "pt"], data_fol=tmp_path, omw_entries=_omw())
    assert summary.gloss_overrides_applied == 0
    assert summary.gloss_overrides_stale == 1
