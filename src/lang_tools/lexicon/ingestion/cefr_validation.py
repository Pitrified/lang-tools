"""Validate the estimated CEFR bands against a graded list (phase 6, step 8).

Kelly (en/it) is **CC-BY-NC-SA and validation-only**: nothing here writes to the
corpus, and no graded label is ever merged into a shipped table. The module
exists so the validation is reproducible package code rather than notebook
cells, and so the cutoffs in `enrich.CEFR_CUTOFFS` can be re-fitted when the
score changes.

What Kelly can and cannot settle:
    It **can** validate the score's *ordering* - the rank correlation between our
    difficulty score and Kelly's bands is 0.608 (en) and 0.614 (it), and the
    Italian figure matters most, because the score was fitted on English alone.

    It **cannot** set the absolute scale. Kelly grades the 7,549 most frequent
    words, so its own "C2" means "least frequent of the common head", not
    "hardest word in the language". WordNet is mostly specialist vocabulary that
    sits past the end of any graded list, so matching Kelly's proportions on the
    words it covers necessarily pushes everything it does not cover into the top
    band. That is a property of the two vocabularies, not a calibration error.

Circularity caveat (phase 5.54, decision 2026-06-21):
    Kelly's bands were themselves built largely from corpus frequency, and token
    frequency is the heaviest term in our score. Agreement therefore confirms the
    pipeline is internally consistent; it is not independent evidence about
    human-perceived difficulty.
"""

from __future__ import annotations

import statistics
from typing import TYPE_CHECKING

from lang_tools.lexicon.ingestion.enrich import CEFR_BANDS
from lang_tools.lexicon.ingestion.enrich import difficulty_score
from lang_tools.lexicon.ingestion.enrich import hypernym_depths
from lang_tools.lexicon.ingestion.enrich import score_to_band

if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence
    from pathlib import Path

#: A graded-list observation: our difficulty score for a form, and the band the
#: graded list assigns it.
GradedPair = tuple[float, str]


class NoGradedPairsError(ValueError):
    """Raised when a validation is asked to run with nothing to validate."""

    def __init__(self) -> None:
        """Initialize with guidance on the likely cause."""
        super().__init__(
            "No graded pairs: the corpus and the graded list share no forms "
            "(check the language and that the list is staged).",
        )


def fit_cutoffs(pairs: Sequence[GradedPair]) -> tuple[float, ...]:
    """Fit band cutoffs so our band proportions match the graded list's.

    Quantile matching: the graded list's share of each band, read off our scores
    sorted ascending. This calibrates the scale to the *covered* vocabulary, so
    every form the list does not cover lands in the top band - see the module
    docstring on why that is expected rather than a fault.

    Args:
        pairs: ``(score, band)`` observations; bands outside `CEFR_BANDS` are
            ignored.

    Returns:
        Five ascending cutoffs, suitable for `enrich.CEFR_CUTOFFS`.

    Raises:
        NoGradedPairsError: When no usable pair is supplied.
    """
    usable = [(score, band) for score, band in pairs if band in CEFR_BANDS]
    if not usable:
        raise NoGradedPairsError
    scores = sorted(score for score, _ in usable)
    total = len(usable)
    counts: dict[str, int] = dict.fromkeys(CEFR_BANDS, 0)
    for _, band in usable:
        counts[band] += 1

    cutoffs: list[float] = []
    cumulative = 0
    for band in CEFR_BANDS[:-1]:
        cumulative += counts[band]
        index = min(cumulative, total - 1)
        cutoffs.append(scores[index])
    return tuple(cutoffs)


def band_agreement(
    pairs: Sequence[GradedPair],
    cutoffs: Sequence[float],
) -> dict[str, float]:
    """Measure how often our banding matches the graded list.

    Args:
        pairs: ``(score, band)`` observations.
        cutoffs: The cutoffs to band the scores with.

    Returns:
        ``n`` (pairs compared), ``exact`` and ``within_one`` (fractions), and
        ``mean_offset`` in bands - negative when we call words easier than the
        list does.

    Raises:
        NoGradedPairsError: When no usable pair is supplied.
    """
    usable = [(score, band) for score, band in pairs if band in CEFR_BANDS]
    if not usable:
        raise NoGradedPairsError
    offsets = [
        CEFR_BANDS.index(score_to_band(score, cutoffs)) - CEFR_BANDS.index(band)
        for score, band in usable
    ]
    return {
        "n": float(len(usable)),
        "exact": sum(1 for o in offsets if o == 0) / len(offsets),
        "within_one": sum(1 for o in offsets if abs(o) <= 1) / len(offsets),
        "mean_offset": statistics.mean(offsets),
    }


def rank_correlation(pairs: Sequence[GradedPair]) -> float:
    """Return Spearman's rho between our score and the graded list's bands.

    This is the figure Kelly can actually support: whether the score *orders*
    vocabulary the way a graded list does, independent of where the band
    boundaries sit.

    Args:
        pairs: ``(score, band)`` observations.

    Returns:
        Spearman's rho in ``[-1, 1]``; positive means a higher score goes with a
        harder band, which is the expected direction.

    Raises:
        NoGradedPairsError: When no usable pair is supplied.
    """
    usable = [(score, band) for score, band in pairs if band in CEFR_BANDS]
    if not usable:
        raise NoGradedPairsError
    scores = _ranks([score for score, _ in usable])
    bands = _ranks([float(CEFR_BANDS.index(band)) for _, band in usable])
    mean_s, mean_b = statistics.mean(scores), statistics.mean(bands)
    numerator = sum(
        (s - mean_s) * (b - mean_b) for s, b in zip(scores, bands, strict=True)
    )
    denominator = (
        sum((s - mean_s) ** 2 for s in scores) * sum((b - mean_b) ** 2 for b in bands)
    ) ** 0.5
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _ranks(values: Sequence[float]) -> list[float]:
    """Return 1-based ranks, averaging ties (as Spearman requires)."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        stop = start
        while stop + 1 < len(order) and values[order[stop + 1]] == values[order[start]]:
            stop += 1
        average = (start + stop) / 2 + 1
        for position in range(start, stop + 1):
            ranks[order[position]] = average
        start = stop + 1
    return ranks


def corpus_form_scores(data_fol: Path, language: str) -> dict[str, float]:
    """Recompute each form's easiest difficulty score from a built corpus.

    The score is not persisted (only the band it produces is), so validating or
    re-fitting means recomputing it from the same inputs the build used: the
    stored token frequency and concept commonness, plus hypernym depth recomputed
    from the shipped edges.

    Args:
        data_fol: Project data folder holding the built corpus.
        language: ISO 639-1 code to score.

    Returns:
        ``{lowercased form: easiest score across its senses}``.

    Raises:
        StoreDependencyMissingError: When the ``store`` extra (duckdb) is absent.
    """
    from lang_tools.lexicon.codec import LEXICON_SUBDIR  # noqa: PLC0415
    from lang_tools.lexicon.codec import _load_table  # noqa: PLC0415
    from lang_tools.lexicon.quality import _connect  # noqa: PLC0415

    concepts = _load_table("concepts", data_fol=data_fol)
    relations = _load_table("concept_relations", data_fol=data_fol)
    depths = hypernym_depths(concepts, relations)
    commonness = {concept.id: concept.commonness for concept in concepts}

    corpus = data_fol / LEXICON_SUBDIR
    con = _connect()
    try:
        rows = con.execute(
            f"""
SELECT lower(l.text), l.text, s.concept_id, s.token_frequency
FROM read_parquet('{corpus / "senses" / f"{language}.parquet"}') s
JOIN read_parquet('{corpus / "lemmas" / f"{language}.parquet"}') l ON l.id = s.lemma_id
""",  # noqa: S608 - paths are ours, not user input
        ).fetchall()
    finally:
        con.close()

    scores: dict[str, float] = {}
    for form, text, concept_id, zipf in rows:
        score = difficulty_score(
            zipf=zipf,
            commonness=commonness.get(concept_id),
            depth=depths.get(concept_id),
            length=len(text),
        )
        if form not in scores or score < scores[form]:
            scores[form] = score
    return scores


def staged_graded_list(data_fol: Path, language: str) -> dict[str, str]:
    """Read a staged graded list into ``{lowercased form: band}``.

    Reads the validation-only staging cache written by `staging.cefr`; the list
    is never merged into the corpus.

    A form graded more than once keeps its **easiest** band. Kelly lists a word
    per part of speech, so 7,549 English rows cover 6,756 distinct forms and
    `back` / `round` appear at two or three levels. Taking the easiest mirrors
    what we do on our own side (a form's score is its easiest sense), and keeping
    whichever row happened to be read last would make the measurement depend on
    file order.

    Args:
        data_fol: Project data folder.
        language: ISO 639-1 code of the staged list.

    Returns:
        The graded list as a mapping. Empty when the list is not staged.
    """
    from lang_tools.lexicon.ingestion.staging.base import dataset_dir  # noqa: PLC0415
    from lang_tools.lexicon.quality import _connect  # noqa: PLC0415

    path = dataset_dir(data_fol, "cefr") / f"{language}.parquet"
    if not path.exists():
        return {}
    con = _connect()
    try:
        rows = con.execute(
            f"SELECT lower(word), level FROM read_parquet('{path}')",  # noqa: S608
        ).fetchall()
    finally:
        con.close()

    easiest: dict[str, str] = {}
    for form, band in rows:
        if band not in CEFR_BANDS:
            continue
        current = easiest.get(form)
        if current is None or CEFR_BANDS.index(band) < CEFR_BANDS.index(current):
            easiest[form] = band
    return easiest


def graded_pairs(
    scores_by_form: Mapping[str, float],
    graded_by_form: Mapping[str, str],
) -> list[GradedPair]:
    """Join our per-form scores to a graded list on the lowercased form.

    A form's score is the *easiest* of its senses, because a graded list grades
    the word as a learner meets it, not each meaning separately.

    Args:
        scores_by_form: ``{lowercased form: easiest difficulty score}``.
        graded_by_form: ``{lowercased form: band}`` from the graded list.

    Returns:
        One pair per form present in both.
    """
    return [
        (scores_by_form[form], band)
        for form, band in graded_by_form.items()
        if form in scores_by_form
    ]
