"""Enrichment stage: per-sense frequency and CEFR complexity (phase 6).

The pure core of phase 6. It takes the transformed tables plus two inputs - the
per-form Zipf mapping from `sources.frequency` and the SemCor counts
`sources.omw` carried through the ILI grouping - and fills the `Sense` fields
phase 2 defined and left empty, plus `Concept.commonness`.

No I/O and no optional imports, so every rule below is unit-testable from
in-memory models.

Why this is a build stage:
    Phase 5.58 established that a rebuild regenerates every column, so a signal
    computed post hoc into the Parquet is silently reverted by the next
    `build_initial`. The SemCor join forces the same conclusion independently: the
    corpus does not persist the ILI, so the counts can only be attributed while
    the grouping is still open, upstream of the write.

The signals:
    **Token frequency** is language-level - how common a *form* is - so it is the
    lemma's Zipf, copied onto each of its senses (`Sense.token_frequency` is
    documented as shared across senses).

    **Sense frequency** splits that across the lemma's senses. The split happens
    in linear frequency space, never on the log-scaled Zipf: converting with
    `zipf_to_linear`, apportioning, and converting back is the only arithmetic
    that means anything. Weights are the concepts' SemCor totals, Laplace
    smoothed so an untagged sense keeps a floor instead of collapsing to zero.

    **Commonness** is the concept-level signal that propagates: SemCor is English
    only, but senses share the ILI, so one value serves every language (phase 5.54
    Topic 3 measured it predicting es 0.34 / it 0.49 lemma frequency).

    **CEFR** is a concept-level score (commonness and hypernym depth) plus a thin
    per-language overlay (token frequency, form length), banded by fixed cutoffs.
    Since no graded list is ever shipped (Kelly is CC-BY-NC-SA, validation only),
    every band is estimated - `cefr_is_estimated` is `True` everywhere, English
    included. That is honest, not decorative.
"""

from __future__ import annotations

from collections import deque
import math
from typing import TYPE_CHECKING

from loguru import logger as lg

from lang_tools.lexicon.ingestion.sources.frequency import is_composed
from lang_tools.lexicon.relations import RELATION_HYPERNYM

if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence

    from lang_tools.lexicon.concept import Concept
    from lang_tools.lexicon.ingestion.transform import TaggedTables
    from lang_tools.lexicon.lemma import Lemma
    from lang_tools.lexicon.relations import ConceptRelation
    from lang_tools.lexicon.sense import Sense

#: Language whose senses can be non-estimated: the only one with a measured sense
#: split (SemCor). Everything else borrows the English distribution.
MEASURED_LANGUAGE = "en"

#: Laplace smoothing added to every sense weight before normalizing, so a sense
#: SemCor never tagged keeps a share instead of collapsing to zero frequency.
WEIGHT_SMOOTHING = 1.0

#: Zipf is log10 occurrences per billion words, so linear frequency is
#: ``10 ** (zipf - ZIPF_OFFSET)``.
ZIPF_OFFSET = 9.0

#: CEFR bands, easiest first. Fixed vocabulary; `cefr_level` is one of these.
CEFR_BANDS = ("A1", "A2", "B1", "B2", "C1", "C2")

#: Score cutoffs between adjacent bands (5 cutoffs for 6 bands), ascending with
#: difficulty. **Fitted** on the English lemmas Kelly covers, by matching Kelly's
#: own band proportions on that subset (2026-09-02). Measured against Kelly on
#: the shipped corpus: exact agreement 41.2% and within-one-band 74.4% (en),
#: against 20.8% / 49.4% for the hand-guessed values they replaced.
#:
#: Applied unchanged to every language, because the inputs are corpus-normalized
#: and re-quantiling per language would force an identical band histogram
#: everywhere, destroying the cross-language comparison the concept-level signal
#: exists to give. The *ordering* transfers: rank correlation with Kelly is 0.632
#: in English and 0.661 in Italian, a language the cutoffs were never fitted on.
#:
#: The *absolute* scale does not fully transfer, and the gap is measured rather
#: than assumed: Italian sits at a mean offset of +1.23 bands (we call its words
#: harder than Kelly-it does), against +0.17 for English. A per-language offset
#: correction is deliberately not invented here - it would need a graded list per
#: language to fit, and three of the five have none.
#:
#: Consequence, stated because the histogram looks alarming: 82% of the corpus
#: lands in C2. That is not a miscalibration. Kelly grades the 7,549 most frequent
#: words, so its own "C2" means "least frequent of the common head", not "hardest
#: word in the language" - and WordNet is overwhelmingly specialist vocabulary
#: (`Tasmanian devil`, taxonomic names) that sits beyond any graded list. Our C2
#: is therefore a catch-all "past the end of the syllabus" bucket, and the bands
#: that matter to a learner (A1-B1, ~7.7% of senses, ~38k) are the ones Kelly can
#: actually speak to.
CEFR_CUTOFFS = (0.2774, 0.3387, 0.4015, 0.4410, 0.4764)

#: Weights of the difficulty score's terms; they sum to 1.0.
#: Lemma frequency dominates because it is the strongest measured signal against
#: Kelly (pearson -0.66, phase 5.54 Topic 5); the concept terms carry the
#: cross-language part; length is a small tiebreak.
WEIGHT_FREQUENCY = 0.55
WEIGHT_COMMONNESS = 0.20
WEIGHT_DEPTH = 0.15
WEIGHT_LENGTH = 0.10

#: Zipf range mapped onto ``[0, 1]`` for the score. 1.0 is vanishingly rare, 7.0
#: is "the", so the band edges sit inside the range rather than on it.
ZIPF_FLOOR = 1.0
ZIPF_CEILING = 7.0

#: Hypernym depth mapped onto ``[0, 1]``; WordNet's noun hierarchy bottoms out
#: around 20 levels, so deeper than this is saturated rather than scaled.
DEPTH_CEILING = 20.0

#: Form length mapped onto ``[0, 1]``, in characters.
LENGTH_FLOOR = 3.0
LENGTH_CEILING = 18.0

#: Difficulty assumed when a term has no value at all (an unknown form, a concept
#: with no English member). Mid-scale, so a missing input neither flatters nor
#: penalizes the sense - it just stops carrying information.
NEUTRAL = 0.5


def zipf_to_linear(zipf: float) -> float:
    """Convert a Zipf value to linear frequency (occurrences per word)."""
    return 10.0 ** (zipf - ZIPF_OFFSET)


def linear_to_zipf(linear: float) -> float:
    """Convert a linear frequency back to the Zipf scale."""
    return math.log10(linear) + ZIPF_OFFSET


def _scale(value: float, low: float, high: float) -> float:
    """Map `value` from ``[low, high]`` onto ``[0, 1]``, clamping outside it."""
    if high <= low:
        return NEUTRAL
    return min(1.0, max(0.0, (value - low) / (high - low)))


def commonness_score(semcor_total: int) -> float:
    """Return the stored commonness value for a SemCor total.

    ``log10(1 + total)`` compresses a distribution phase 5.54 measured as heavily
    skewed (median 2, max 10,742), so the head does not swamp everything else.

    Args:
        semcor_total: Summed SemCor counts over the concept's English senses.

    Returns:
        The commonness value stored on `Concept.commonness`.
    """
    return math.log10(1.0 + semcor_total)


def hypernym_depths(
    concepts: Sequence[Concept],
    relations: Sequence[ConceptRelation],
) -> dict[str, int]:
    """Return each concept's shortest distance to a hypernym root.

    A root is a concept with no hypernym of its own. Depth is computed here on
    every build rather than persisted: it is derived from the shipped edges, and
    nothing consumes it but the CEFR score. If a consumer ever needs it, persist
    it from the build - the store is shaped for point lookups and bounded
    adjacency, so an unbounded traversal at query time would be the same class of
    performance bug phase 5.3 spent a phase removing.

    Args:
        concepts: All concepts (so isolated ones are still roots at depth 0).
        relations: Concept relation edges; only hypernym edges are read, directed
            from the specific concept (``a``) to its broader one (``b``).

    Returns:
        ``{concept_id: depth}``, 0 for a root. Concepts in a hypernym cycle are
        reached from whatever root can see them, and are absent if none can.
    """
    parents: dict[str, list[str]] = {}
    children: dict[str, list[str]] = {}
    for rel in relations:
        if rel.relation_type != RELATION_HYPERNYM:
            continue
        parents.setdefault(rel.concept_id_a, []).append(rel.concept_id_b)
        children.setdefault(rel.concept_id_b, []).append(rel.concept_id_a)

    depths: dict[str, int] = {}
    queue: deque[str] = deque()
    for concept in concepts:
        if not parents.get(concept.id):
            depths[concept.id] = 0
            queue.append(concept.id)
    while queue:
        current = queue.popleft()
        for child in children.get(current, ()):
            if child not in depths:
                depths[child] = depths[current] + 1
                queue.append(child)
    return depths


def difficulty_score(
    *,
    zipf: float | None,
    commonness: float | None,
    depth: int | None,
    length: int,
) -> float:
    """Blend the four difficulty terms into a ``[0, 1]`` score (higher = harder).

    Args:
        zipf: The form's token frequency, or ``None`` when unknown.
        commonness: The concept's commonness, or ``None`` when it has no English
            member to measure.
        depth: Hypernym depth of the concept, or ``None`` when unreachable.
        length: Length of the surface form in characters.

    Returns:
        The blended score.
    """
    freq_term = (
        NEUTRAL if zipf is None else 1.0 - _scale(zipf, ZIPF_FLOOR, ZIPF_CEILING)
    )
    common_term = (
        NEUTRAL
        if commonness is None
        else 1.0 - _scale(commonness, 0.0, commonness_score(1000))
    )
    depth_term = NEUTRAL if depth is None else _scale(depth, 0.0, DEPTH_CEILING)
    length_term = _scale(length, LENGTH_FLOOR, LENGTH_CEILING)
    return (
        WEIGHT_FREQUENCY * freq_term
        + WEIGHT_COMMONNESS * common_term
        + WEIGHT_DEPTH * depth_term
        + WEIGHT_LENGTH * length_term
    )


def score_to_band(score: float, cutoffs: Sequence[float] = CEFR_CUTOFFS) -> str:
    """Map a difficulty score to its CEFR band.

    Args:
        score: The blended difficulty score.
        cutoffs: Band boundaries, ascending. Defaults to the fitted
            `CEFR_CUTOFFS`; `cefr_validation` passes candidates when re-fitting.

    Returns:
        The band whose range contains `score`.
    """
    for band, cutoff in zip(CEFR_BANDS, cutoffs, strict=False):
        if score < cutoff:
            return band
    return CEFR_BANDS[-1]


def _sense_shares(weights: Sequence[int]) -> list[float]:
    """Return smoothed, normalized shares for one lemma's sense weights."""
    smoothed = [w + WEIGHT_SMOOTHING for w in weights]
    total = sum(smoothed)
    return [s / total for s in smoothed]


def enrich(
    tables: TaggedTables,
    *,
    zipf_by_form: Mapping[tuple[str, str], float],
) -> dict[str, int]:
    """Populate frequency and CEFR on the tables, in place.

    Args:
        tables: The transformed tables; `sense_counts` / `concept_counts` supply
            the SemCor weights, and the sense and concept rows are mutated.
        zipf_by_form: ``{(text, language): zipf}`` from `sources.frequency`; a
            missing key means the form has no known frequency.

    Returns:
        Counts for the build summary and manifest: how many senses got a token
        frequency, how many are flagged estimated, how many concepts got a
        commonness value, and the per-band totals.
    """
    commonness_by_concept = _apply_commonness(tables)
    depths = hypernym_depths(tables.concepts, tables.concept_relations)
    lemma_by_id = {lemma.id: lemma for lemma in tables.lemmas}

    senses_by_lemma: dict[str, list[Sense]] = {}
    for sense in tables.senses:
        senses_by_lemma.setdefault(sense.lemma_id, []).append(sense)

    stats = {"with_frequency": 0, "estimated": 0, "with_band": 0}
    bands: dict[str, int] = dict.fromkeys(CEFR_BANDS, 0)
    for lemma_id, group in senses_by_lemma.items():
        lemma = lemma_by_id.get(lemma_id)
        if lemma is None:
            # A sense whose lemma was dropped is a dangling edge the gate fails
            # on; skip it here rather than inventing values for a row that
            # should not exist.
            continue
        _enrich_lemma_senses(
            lemma,
            group,
            zipf=zipf_by_form.get((lemma.text, lemma.language)),
            counts=tables.sense_counts,
            commonness=commonness_by_concept,
            depths=depths,
            stats=stats,
            bands=bands,
        )

    lg.info(
        "Enriched {} senses: {} with a token frequency, {} estimated; bands {}",
        len(tables.senses),
        stats["with_frequency"],
        stats["estimated"],
        bands,
    )
    return {**stats, **{f"band_{band}": n for band, n in bands.items()}}


def _apply_commonness(tables: TaggedTables) -> dict[str, float]:
    """Set `Concept.commonness` from the SemCor totals; return it by concept id."""
    by_concept: dict[str, float] = {}
    for concept in tables.concepts:
        total = tables.concept_counts.get(concept.id)
        if total is None:
            # No English member at all - distinct from "tagged zero times".
            continue
        concept.commonness = commonness_score(total)
        by_concept[concept.id] = concept.commonness
    return by_concept


def _enrich_lemma_senses(
    lemma: Lemma,
    senses: Sequence[Sense],
    *,
    zipf: float | None,
    counts: Mapping[tuple[str, str], int],
    commonness: Mapping[str, float],
    depths: Mapping[str, int],
    stats: dict[str, int],
    bands: dict[str, int],
) -> None:
    """Fill one lemma's senses: token frequency, split sense frequency, CEFR."""
    weights = [counts.get((lemma.id, sense.concept_id), 0) for sense in senses]
    shares = _sense_shares(weights)
    composed = is_composed(lemma.text)
    linear = None if zipf is None else zipf_to_linear(zipf)

    for sense, weight, share in zip(senses, weights, shares, strict=True):
        sense.token_frequency = zipf
        if linear is not None:
            sense.sense_frequency = linear_to_zipf(linear * share)
            stats["with_frequency"] += 1
        # Measured only for an English single-word form on a sense SemCor tagged;
        # every other split borrows the English distribution or is composed.
        measured = (
            lemma.language == MEASURED_LANGUAGE and weight > 0 and not composed
        )
        sense.frequency_is_estimated = not measured
        if sense.frequency_is_estimated:
            stats["estimated"] += 1

        band = score_to_band(
            difficulty_score(
                zipf=zipf,
                commonness=commonness.get(sense.concept_id),
                depth=depths.get(sense.concept_id),
                length=len(lemma.text),
            ),
        )
        sense.cefr_level = band
        # Never from a graded list: Kelly is validation-only, so all bands are
        # estimates, English included.
        sense.cefr_is_estimated = True
        bands[band] += 1
        stats["with_band"] += 1
