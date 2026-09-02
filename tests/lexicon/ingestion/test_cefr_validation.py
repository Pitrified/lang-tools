"""Tests for the graded-list validation helpers (`ingestion.cefr_validation`).

Pure math over synthetic pairs; no staged Kelly list and no corpus involved.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from lang_tools.lexicon.ingestion.cefr_validation import NoGradedPairsError
from lang_tools.lexicon.ingestion.cefr_validation import band_agreement
from lang_tools.lexicon.ingestion.cefr_validation import fit_cutoffs
from lang_tools.lexicon.ingestion.cefr_validation import graded_pairs
from lang_tools.lexicon.ingestion.cefr_validation import rank_correlation
from lang_tools.lexicon.ingestion.cefr_validation import staged_graded_list
from lang_tools.lexicon.ingestion.enrich import CEFR_BANDS
from lang_tools.lexicon.ingestion.staging.base import dataset_dir
from lang_tools.lexicon.ingestion.staging.base import write_rows_parquet
from lang_tools.lexicon.ingestion.staging.cefr import CEFR_COLUMNS

if TYPE_CHECKING:
    from pathlib import Path


def _perfectly_ordered_pairs() -> list[tuple[float, str]]:
    """Ten forms per band, scores ascending exactly with difficulty."""
    return [
        (index * 0.01 + CEFR_BANDS.index(band), band)
        for band in CEFR_BANDS
        for index in range(10)
    ]


def test_fitted_cutoffs_reproduce_the_graded_lists_proportions() -> None:
    pairs = _perfectly_ordered_pairs()
    cutoffs = fit_cutoffs(pairs)
    agreement = band_agreement(pairs, cutoffs)
    # The score orders these perfectly, so quantile matching recovers the bands.
    assert agreement["exact"] == 1.0


def test_fitted_cutoffs_are_ascending() -> None:
    cutoffs = fit_cutoffs(_perfectly_ordered_pairs())
    assert len(cutoffs) == len(CEFR_BANDS) - 1
    assert list(cutoffs) == sorted(cutoffs)


def test_fitting_follows_a_skewed_list() -> None:
    # A list that is nearly all C2 should push the cutoffs down, so that almost
    # everything lands in the top band.
    pairs = [(0.1, "A1")] + [(0.5 + i * 0.001, "C2") for i in range(99)]
    cutoffs = fit_cutoffs(pairs)
    agreement = band_agreement(pairs, cutoffs)
    assert agreement["exact"] > 0.9


def test_mean_offset_signs_the_direction_of_the_error() -> None:
    # Cutoffs far above every score: everything is called A1, i.e. far easier
    # than the list says. That must read as a negative offset.
    pairs = [(0.1, "C1"), (0.2, "C2")]
    agreement = band_agreement(pairs, cutoffs=(9.0, 9.1, 9.2, 9.3, 9.4))
    assert agreement["mean_offset"] < 0
    assert agreement["exact"] == 0.0


def test_rank_correlation_is_near_one_when_the_ordering_matches() -> None:
    # Not exactly 1.0, and it cannot be: the ten scores inside a band are all
    # distinct while their bands tie, so the tied ranks cap rho just below 1.
    # This is the ceiling any real measurement against a 6-band list runs into.
    assert rank_correlation(_perfectly_ordered_pairs()) > 0.98


def test_rank_correlation_is_negative_when_the_ordering_is_reversed() -> None:
    reversed_pairs = [
        (-score, band) for score, band in _perfectly_ordered_pairs()
    ]
    assert rank_correlation(reversed_pairs) < -0.9


def test_rank_correlation_survives_ties() -> None:
    # Every score identical: no ordering information, and no ZeroDivisionError.
    assert rank_correlation([(0.5, band) for band in CEFR_BANDS]) == 0.0


def test_graded_pairs_joins_on_shared_forms_only() -> None:
    pairs = graded_pairs({"house": 0.2, "quark": 0.9}, {"house": "A1", "zzz": "C2"})
    assert pairs == [(0.2, "A1")]


def test_unknown_bands_are_ignored_not_fatal() -> None:
    pairs = [(0.1, "A1"), (0.2, "not-a-band")]
    assert band_agreement(pairs, cutoffs=(0.15, 0.2, 0.3, 0.4, 0.5))["n"] == 1.0


def test_no_usable_pairs_raises() -> None:
    with pytest.raises(NoGradedPairsError):
        fit_cutoffs([])
    with pytest.raises(NoGradedPairsError):
        band_agreement([(0.1, "unknown")], cutoffs=(0.1, 0.2, 0.3, 0.4, 0.5))
    with pytest.raises(NoGradedPairsError):
        rank_correlation([])


def test_staged_list_keeps_the_easiest_band_for_a_repeated_form(
    tmp_path: Path,
) -> None:
    # Kelly lists a word once per part of speech, so 7,549 English rows cover
    # 6,756 forms and `round` appears at three levels. Keeping whichever row was
    # read last would make the measurement depend on file order.
    write_rows_parquet(
        [
            {"word": "Round", "level": "C1"},
            {"word": "round", "level": "A2"},
            {"word": "round", "level": "B2"},
            {"word": "quark", "level": "not-a-band"},
        ],
        dataset_dir(tmp_path, "cefr") / "en.parquet",
        columns=CEFR_COLUMNS,
    )
    staged = staged_graded_list(tmp_path, "en")
    assert staged == {"round": "A2"}


def test_missing_staged_list_is_empty_not_an_error(tmp_path: Path) -> None:
    assert staged_graded_list(tmp_path, "fr") == {}
