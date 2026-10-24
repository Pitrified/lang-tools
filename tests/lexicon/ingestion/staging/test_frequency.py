"""Tests for the frequency staging adapter (`ingestion.staging.frequency`).

``wordfreq`` is optional and ships with the ``ingest`` extra since phase 6 (it
became a build input): the happy path is skipped when it is absent, and the
dependency guard is always checked.
"""

from __future__ import annotations

import importlib.util

import pytest

from lang_tools.lexicon.ingestion.deps import OptionalDependencyMissingError
from lang_tools.lexicon.ingestion.staging.frequency import _require_wordfreq
from lang_tools.lexicon.ingestion.staging.frequency import frequency_rows

_HAS_WORDFREQ = importlib.util.find_spec("wordfreq") is not None


def test_dependency_error_names_the_package_and_its_extra() -> None:
    err = OptionalDependencyMissingError("wordfreq", "ingest")
    assert isinstance(err, ImportError)
    assert "wordfreq" in str(err)
    # The extra has to come from the error, not be hardcoded per call site:
    # `wordfreq` moved enrich -> ingest in phase 6 and the message followed it.
    assert "ingest" in str(err)
    assert err.package == "wordfreq"
    assert err.extra == "ingest"


@pytest.mark.skipif(_HAS_WORDFREQ, reason="wordfreq installed; guard not triggered")
def test_require_wordfreq_raises_when_absent() -> None:
    with pytest.raises(OptionalDependencyMissingError):
        _require_wordfreq()


@pytest.mark.skipif(not _HAS_WORDFREQ, reason="needs the ingest extra (wordfreq)")
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
