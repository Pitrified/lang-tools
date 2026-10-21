"""Tests for the non-English gloss backfill (`ingestion.gloss_backfill`)."""

from pathlib import Path

from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.ingestion.gloss_backfill import BackfillItem
from lang_tools.lexicon.ingestion.gloss_backfill import accept_run
from lang_tools.lexicon.ingestion.gloss_backfill import check_glosses
from lang_tools.lexicon.ingestion.gloss_backfill import chunk_items
from lang_tools.lexicon.ingestion.gloss_backfill import missing_glosses
from lang_tools.lexicon.ingestion.gloss_backfill import review_sample
from lang_tools.lexicon.ingestion.pipeline import build_initial
from lang_tools.lexicon.ingestion.sources.omw import SynsetEntry
from lang_tools.lexicon.lemma_store import LexiconStore
from lang_tools.lexicon.maintenance import GLOSS_BACKFILL_FILE
from lang_tools.lexicon.maintenance import GlossProposal
from lang_tools.lexicon.maintenance import apply_gloss_backfill
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import write_jsonl
from lang_tools.lexicon.quality import run_quality_checks
from lang_tools.llm.gloss_translate import GlossTranslateOutput
from lang_tools.llm.gloss_translate import KeyedGloss

_HOUSE = "c__house__0011aabbccdd"


def _entries() -> list[SynsetEntry]:
    return [
        SynsetEntry("en", "en-1", "i1", "a dwelling", ("house",), pos="n"),
        SynsetEntry("pt", "pt-1", "i1", None, ("casa",), pos="n"),
        SynsetEntry("es", "es-1", "i1", "una vivienda", ("casa",), pos="n"),
    ]


def _item(language: str = "pt") -> BackfillItem:
    return BackfillItem(
        concept_id=_HOUSE,
        language=language,
        english_definition="a dwelling that serves as living quarters",
        english_members=("house",),
        target_members=("casa",),
    )


def _out(definition: str, key: str = "pt:0011aabbccdd") -> GlossTranslateOutput:
    return GlossTranslateOutput(glosses=[KeyedGloss(key=key, definition=definition)])


def test_worklist_is_the_missing_languages_only(tmp_path: Path) -> None:
    build_initial(["en", "pt", "es"], data_fol=tmp_path, omw_entries=_entries())
    items = missing_glosses(tmp_path)
    # es already has an OMW gloss; pt does not.
    assert [(i.language, i.target_members) for i in items] == [("pt", ("casa",))]


def test_chunks_are_per_language_and_deterministic() -> None:
    items = [_item("pt"), _item("fr")]
    chunks = chunk_items(items, size=1)
    assert [key for key, _ in chunks] == ["fr:0011aabbccdd", "pt:0011aabbccdd"]
    assert chunks[1][1].language_name == "Portuguese"
    assert "Brazilian" in chunks[1][1].variety
    assert chunk_items(list(reversed(items)), size=1) == chunks


def test_screen_accepts_a_gloss_and_rejects_the_bad_kinds() -> None:
    def _verdict(text: str) -> tuple[str, str]:
        (row,) = check_glosses([_item()], _out(text))
        return row.status, row.rationale

    assert _verdict("Construção que serve de habitação.") == ("proposed", "")
    assert _verdict("") == ("rejected", "missing")
    assert _verdict("Casa.") == ("rejected", "restates a member word")
    assert _verdict("a dwelling that serves as living quarters") == (
        "rejected",
        "untranslated",
    )
    assert _verdict("x" * 500) == ("rejected", "runaway length")
    (row,) = check_glosses([_item()], _out("o Sol encontra\u2011se"))
    assert row.proposed_definition == "o Sol encontra-se"


def test_sample_and_accept_follow_the_review() -> None:
    rows = [
        GlossProposal(
            concept_id=_HOUSE,
            language=lang,
            current_definition="",
            proposed_definition=f"gloss {i}",
            status=status,  # pyright: ignore[reportArgumentType]
        )
        for i, (lang, status) in enumerate(
            [
                ("pt", "proposed"),
                ("pt", "proposed"),
                ("fr", "proposed"),
                ("fr", "rejected"),
            ],
        )
    ]
    assert len(review_sample(rows, per_language=1)) == 2  # rejected rows excluded
    accepted = accept_run(rows, languages=["pt"])
    assert [r.status for r in accepted] == [
        "accepted",
        "accepted",
        "proposed",
        "rejected",
    ]


def test_backfill_fills_gaps_only_and_tags_the_gloss() -> None:
    concept = Concept(id=_HOUSE, definitions={"en": "a dwelling", "es": "vivienda"})

    def _row(lang: str) -> GlossProposal:
        return GlossProposal(
            concept_id="c__old-slug__0011aabbccdd",  # matched by key, not slug
            language=lang,
            current_definition="",
            proposed_definition=f"generated {lang}",
            status="accepted",
        )

    counts = apply_gloss_backfill([concept], backfill=[_row("pt"), _row("es")])
    assert counts == (1, 1, 0)  # filled, skipped (es exists), stale
    assert concept.definitions == {
        "en": "a dwelling",
        "es": "vivienda",
        "pt": "generated pt",
    }
    assert concept.definition_sources == {"pt": "llm"}


def test_build_applies_an_accepted_backfill_and_the_gate_counts_it(
    tmp_path: Path,
) -> None:
    build_initial(["en", "pt", "es"], data_fol=tmp_path, omw_entries=_entries())
    (item,) = missing_glosses(tmp_path)
    rows = accept_run(check_glosses([item], _out("Construção para morar.", item.key)))
    write_jsonl(rows, curated_path(tmp_path, GLOSS_BACKFILL_FILE))

    summary = build_initial(
        ["en", "pt", "es"],
        data_fol=tmp_path,
        omw_entries=_entries(),
    )
    assert summary.glosses_backfilled == 1
    (concept,) = LexiconStore.from_data_fol(tmp_path).get_all_concepts()
    assert concept.definitions["pt"] == "Construção para morar."
    assert concept.definition_sources == {"pt": "llm"}

    report = run_quality_checks(tmp_path)
    rows_by_lang = {
        row[0]: row
        for row in {res.name: res for res in report.results}["gloss_provenance"].rows
    }
    assert rows_by_lang["pt"] == ["pt", 1, 1, 0]
    assert rows_by_lang["es"] == ["es", 1, 0, 1]
