"""Tests for the initial-build pipeline (`ingestion.pipeline`).

Drives `build_initial` with in-memory OMW inputs (no network, no ``wn``), then
confirms the source-of-truth Parquet loads back through `LexiconStore` and that
provenance is written on disk but dropped on model load.
"""

from pathlib import Path

import pyarrow.parquet as pq

from lang_tools.lexicon.codec import PROVENANCE_COL
from lang_tools.lexicon.ingestion.acquire import read_manifest
from lang_tools.lexicon.ingestion.enrich import CEFR_BANDS
from lang_tools.lexicon.ingestion.pipeline import build_initial
from lang_tools.lexicon.ingestion.sources.omw import SynsetEntry
from lang_tools.lexicon.lemma_id import lemma_id
from lang_tools.lexicon.lemma_store import LexiconStore
from lang_tools.lexicon.maintenance import GlossProposal
from lang_tools.lexicon.maintenance import gloss_overrides_path
from lang_tools.lexicon.maintenance import write_proposals


def _omw_with_counts() -> list[SynsetEntry]:
    """Return the `_omw` shape, with SemCor counts on the English members."""
    return [
        SynsetEntry(
            "en", "en-1", "i001", "a building for living", ("house",),
            member_counts=(21,), pos="n",
        ),
        SynsetEntry("pt", "pt-1", "i001", "uma moradia", ("casa",), pos="n"),
        SynsetEntry("en", "en-2", "i002", "a flow of water", ("river",), pos="n"),
        SynsetEntry("pt", "pt-2", "i002", "um curso de agua", ("rio",), pos="n"),
    ]


def _omw() -> list[SynsetEntry]:
    return [
        SynsetEntry("en", "en-1", "i001", "a building for living", ("house",), pos="n"),
        SynsetEntry("pt", "pt-1", "i001", "uma moradia", ("casa",), pos="n"),
        SynsetEntry("en", "en-2", "i002", "a flow of water", ("river",), pos="n"),
        SynsetEntry("pt", "pt-2", "i002", "um curso de agua", ("rio",), pos="n"),
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


def test_build_fills_frequency_and_cefr_without_a_post_hoc_pass(
    tmp_path: Path,
) -> None:
    # The whole point of doing this in the build (05.58's rule): the signals are
    # on disk straight out of `build_initial`, so the next rebuild reproduces
    # them instead of reverting them.
    zipf = {("house", "en"): 4.4, ("casa", "pt"): 5.1, ("river", "en"): 4.0}
    summary = build_initial(
        ["en", "pt"],
        data_fol=tmp_path,
        omw_entries=_omw_with_counts(),
        zipf_by_form=zipf,
    )

    store = LexiconStore.from_data_fol(tmp_path)
    senses = [
        sense
        for lemma in store.get_all_lemmas()
        for sense in store.senses_for_lemma(lemma.id)
    ]
    [house] = store.senses_for_lemma(lemma_id("house", "en"))
    assert house.token_frequency == 4.4
    assert house.sense_frequency is not None
    assert house.cefr_level in CEFR_BANDS
    # Every band is an estimate: no graded list is ever merged into the corpus.
    assert all(s.cefr_is_estimated for s in senses)
    # A form we have no frequency for keeps None, not 0.0.
    [rio] = store.senses_for_lemma(lemma_id("rio", "pt"))
    assert rio.token_frequency is None

    assert summary.enrichment["with_frequency"] == 3
    assert summary.enrichment["with_band"] == 4


def test_manifest_pins_the_frequency_source_version(tmp_path: Path) -> None:
    build_initial(
        ["en", "pt"],
        data_fol=tmp_path,
        omw_entries=_omw_with_counts(),
        zipf_by_form={},
    )
    manifest = read_manifest(tmp_path)
    assert manifest is not None
    # A real pin, read from package metadata. `wordfreq` exposes no
    # `__version__`, so the attribute lookup this replaced always recorded the
    # literal string "unknown" and pinned nothing.
    assert manifest["enrichment"]["wordfreq"] != "unknown"


def test_commonness_reaches_the_concepts_on_disk(tmp_path: Path) -> None:
    build_initial(
        ["en", "pt"],
        data_fol=tmp_path,
        omw_entries=_omw_with_counts(),
        zipf_by_form={},
    )
    store = LexiconStore.from_data_fol(tmp_path)
    values = [c.commonness for c in store.get_all_concepts()]
    # Both concepts have an English member, so both are counted; the tagged one
    # scores above the untagged one.
    assert None not in values
    assert max(v for v in values if v is not None) > 0.0
