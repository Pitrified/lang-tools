"""Tests for the initial-build pipeline (`ingestion.pipeline`).

Drives `build_initial` with in-memory OMW/kaikki inputs (no network, no ``wn``),
then confirms the source-of-truth Parquet loads back through `LexiconStore` and
that provenance is written on disk but dropped on model load.
"""

from pathlib import Path

import pyarrow.parquet as pq

from lang_tools.lexicon.codec import PROVENANCE_COL
from lang_tools.lexicon.ingestion.acquire import read_manifest
from lang_tools.lexicon.ingestion.pipeline import build_initial
from lang_tools.lexicon.ingestion.sources.kaikki import KaikkiEntry
from lang_tools.lexicon.ingestion.sources.omw import SynsetEntry
from lang_tools.lexicon.lemma_store import LexiconStore


def _omw() -> list[SynsetEntry]:
    return [
        SynsetEntry("en", "en-1", "i001", "a building for living", ("house",), "n"),
        SynsetEntry("pt", "pt-1", "i001", None, ("casa",), "n"),
        SynsetEntry("en", "en-2", "i002", "a flow of water", ("river",), "n"),
        SynsetEntry("pt", "pt-2", "i002", "um curso de agua", ("rio",), "n"),
    ]


def test_build_writes_parquet_manifest_and_loads_via_store(tmp_path: Path) -> None:
    kaikki = [KaikkiEntry(text="casa", language="pt", definitions=["uma moradia"])]
    summary = build_initial(
        ["en", "pt"],
        data_fol=tmp_path,
        omw_entries=_omw(),
        kaikki_entries=kaikki,
    )

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
    # Gloss coverage came from kaikki enrichment for pt.
    assert concepts[0].definitions["pt"] == "uma moradia"


def test_manifest_pins_languages_and_counts(tmp_path: Path) -> None:
    build_initial(
        ["en", "pt"],
        data_fol=tmp_path,
        omw_entries=_omw(),
        kaikki_entries=[],
        extra_manifest={"wn_version": "0.9.5", "omw_version": "omw:1.4"},
    )
    manifest = read_manifest(tmp_path)
    assert manifest is not None
    assert manifest["languages"] == ["en", "pt"]
    assert manifest["counts"]["concepts"] == 2
    assert manifest["wn_version"] == "0.9.5"
    assert "built_at" in manifest


def test_provenance_written_on_disk_but_dropped_on_load(tmp_path: Path) -> None:
    build_initial(
        ["en", "pt"],
        data_fol=tmp_path,
        omw_entries=_omw(),
        kaikki_entries=[KaikkiEntry(text="casa", language="pt", definitions=["m"])],
    )
    # The Parquet carries the source column...
    table = pq.read_table(tmp_path / "lexicon" / "concepts.parquet")
    assert PROVENANCE_COL in table.column_names
    sources = set(table.column(PROVENANCE_COL).to_pylist())
    assert sources == {"omw", "kaikki"}

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
        kaikki_entries=[],
        sample_data_fol=sample_fol,
        max_sample_concepts=1,
    )
    assert summary.sample_counts["concepts"] == 1
    store = LexiconStore.from_data_fol(sample_fol)
    assert len(store.get_all_concepts()) == 1
