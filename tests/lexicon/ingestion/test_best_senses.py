"""Tests for the reviewed best-sense pins (`ingestion.best_senses`)."""

from typing import TYPE_CHECKING

from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.concept_id import concept_key
from lang_tools.lexicon.ingestion.best_senses import BEST_SENSES_FILE
from lang_tools.lexicon.ingestion.best_senses import BestSense
from lang_tools.lexicon.ingestion.best_senses import apply_best_senses
from lang_tools.lexicon.ingestion.best_senses import apply_pinned_part_of_speech
from lang_tools.lexicon.ingestion.best_senses import load_best_senses
from lang_tools.lexicon.lemma import Lemma
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import write_jsonl
from lang_tools.lexicon.sense import Sense

if TYPE_CHECKING:
    from pathlib import Path

C_CROWD = "c__crowd-workforce__0011aabbccdd"
C_MEN = "c__man-adult__0022bbccddee"


def _senses() -> list[Sense]:
    return [
        Sense(lemma_id="homens", concept_id=C_CROWD),
        Sense(lemma_id="homens", concept_id=C_MEN),
    ]


def test_latest_accepted_row_per_lemma_wins(tmp_path: Path) -> None:
    rows = [
        BestSense(lemma_id="homens", concept_key="0011aabbccdd", status="accepted"),
        BestSense(lemma_id="homens", concept_key="0022bbccddee", status="accepted"),
        BestSense(lemma_id="bem", concept_key="0033ccddeeff", status="accepted"),
        # A later row with no concept retracts the pin on bem.
        BestSense(lemma_id="bem", status="accepted"),
        BestSense(lemma_id="seja", concept_key="0044ddeeff00", status="proposed"),
    ]
    write_jsonl(rows, curated_path(tmp_path, BEST_SENSES_FILE))
    loaded = {row.lemma_id: row.concept_key for row in load_best_senses(tmp_path)}
    assert loaded == {"homens": "0022bbccddee", "bem": None}


def test_missing_file_loads_nothing(tmp_path: Path) -> None:
    assert load_best_senses(tmp_path) == []


def test_apply_pins_the_named_sense_and_counts_stale() -> None:
    senses = _senses()
    rows = [
        BestSense(lemma_id="homens", concept_key=concept_key(C_MEN)),
        BestSense(lemma_id="homens-gone", concept_key="0099aabbccdd"),
        BestSense(lemma_id="bem"),  # keeps the frequency pick
    ]
    assert apply_best_senses(senses, rows) == (1, 1)
    assert [sense.is_best for sense in senses] == [False, True]


def test_a_pinned_lemma_takes_the_class_of_its_card() -> None:
    um = Lemma(text="um", language="pt", part_of_speech="noun")
    hoje = Lemma(text="hoje", language="pt", part_of_speech="noun")
    casa = Lemma(text="casa", language="pt", part_of_speech="noun")
    c_article = "c__a-an__0011aabbccdd"
    c_today = "c__today__0022bbccddee"
    c_odd = "c__odd__0033ccddeeff"
    concepts = [
        Concept(id=c_article, lexfile="det.article"),
        Concept(id=c_today, lexfile="adv.all"),
        Concept(id=c_odd, lexfile="unknown"),
    ]
    senses = [
        Sense(lemma_id=um.id, concept_id=c_article, is_best=True),
        Sense(lemma_id=hoje.id, concept_id=c_today, is_best=True),
        # A pin on a concept with no known class leaves the lemma as it is.
        Sense(lemma_id=casa.id, concept_id=c_odd, is_best=True),
    ]
    assert apply_pinned_part_of_speech([um, hoje, casa], senses, concepts) == 2
    assert [um.part_of_speech, hoje.part_of_speech, casa.part_of_speech] == [
        "determiner",
        "adverb",
        "noun",
    ]
