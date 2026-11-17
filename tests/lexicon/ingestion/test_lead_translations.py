"""Tests for the reviewed lead translations (`ingestion.lead_translations`)."""

from typing import TYPE_CHECKING

from lang_tools.lexicon.concept_id import concept_key
from lang_tools.lexicon.ingestion.lead_translations import LEAD_TRANSLATIONS_FILE
from lang_tools.lexicon.ingestion.lead_translations import LeadTranslation
from lang_tools.lexicon.ingestion.lead_translations import apply_lead_translations
from lang_tools.lexicon.ingestion.lead_translations import load_lead_translations
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import write_jsonl
from lang_tools.lexicon.sense import Sense

if TYPE_CHECKING:
    from pathlib import Path

C_CAREER = "c__career__0011aabbccdd"
C_BEING = "c__existence__0022bbccddee"


def test_latest_accepted_row_per_concept_and_language_wins(tmp_path: Path) -> None:
    rows = [
        LeadTranslation(
            concept_key="0011aabbccdd",
            language="en",
            lemma_id="calling",
            status="accepted",
        ),
        LeadTranslation(
            concept_key="0011aabbccdd",
            language="en",
            lemma_id="career",
            status="accepted",
        ),
        # Another language of the same concept is its own key.
        LeadTranslation(
            concept_key="0011aabbccdd",
            language="it",
            lemma_id="carriera",
            status="accepted",
        ),
        LeadTranslation(
            concept_key="0022bbccddee",
            language="en",
            lemma_id="existence",
            status="accepted",
        ),
        # A later row with no lemma retracts the lead on existence.
        LeadTranslation(concept_key="0022bbccddee", language="en", status="accepted"),
        LeadTranslation(
            concept_key="0033ccddeeff",
            language="en",
            lemma_id="growth",
            status="proposed",
        ),
    ]
    write_jsonl(rows, curated_path(tmp_path, LEAD_TRANSLATIONS_FILE))
    loaded = {row.key: row.lemma_id for row in load_lead_translations(tmp_path)}
    assert loaded == {
        "0011aabbccdd:en": "career",
        "0011aabbccdd:it": "carriera",
        "0022bbccddee:en": None,
    }


def test_missing_file_loads_nothing(tmp_path: Path) -> None:
    assert load_lead_translations(tmp_path) == []


def test_apply_sets_the_named_sense_and_counts_stale() -> None:
    senses = [
        Sense(lemma_id="calling", concept_id=C_CAREER),
        Sense(lemma_id="career", concept_id=C_CAREER),
        Sense(lemma_id="being", concept_id=C_BEING),
    ]
    rows = [
        LeadTranslation(
            concept_key=concept_key(C_CAREER), language="en", lemma_id="career"
        ),
        LeadTranslation(concept_key="0099aabbccdd", language="en", lemma_id="gone"),
        # Keeps the frequency order.
        LeadTranslation(concept_key=concept_key(C_BEING), language="en"),
    ]
    assert apply_lead_translations(senses, rows) == (1, 1)
    assert [sense.is_lead for sense in senses] == [False, True, False]
