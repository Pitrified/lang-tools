"""Tests for the frequency staging adapter (`ingestion.staging.frequency`).

``wordfreq`` is the optional ``enrich`` extra: the happy path is skipped when it
is absent, and the dependency guard is always checked.
"""

from __future__ import annotations

import importlib.util

import pytest

from lang_tools.lexicon.ingestion.staging.frequency import EnrichDependencyMissingError
from lang_tools.lexicon.ingestion.staging.frequency import _require_wordfreq
from lang_tools.lexicon.ingestion.staging.frequency import frequency_rows

_HAS_WORDFREQ = importlib.util.find_spec("wordfreq") is not None


def test_dependency_error_is_an_importerror_with_guidance() -> None:
    err = EnrichDependencyMissingError()
    assert isinstance(err, ImportError)
    assert "enrich" in str(err)


@pytest.mark.skipif(_HAS_WORDFREQ, reason="wordfreq installed; guard not triggered")
def test_require_wordfreq_raises_when_absent() -> None:
    with pytest.raises(EnrichDependencyMissingError):
        _require_wordfreq()


@pytest.mark.skipif(not _HAS_WORDFREQ, reason="needs the enrich extra (wordfreq)")
def test_frequency_rows_are_ranked_descending() -> None:
    rows = frequency_rows("en", top_n=20)
    assert len(rows) == 20
    assert rows[0]["rank"] == 1
    assert [r["rank"] for r in rows] == list(range(1, 21))
    # zipf is non-increasing as rank grows (top_n_list is frequency-ordered).
    previous: float | None = None
    for row in rows:
        zipf = row["zipf"]
        assert isinstance(zipf, float)
        if previous is not None:
            assert zipf <= previous
        previous = zipf
