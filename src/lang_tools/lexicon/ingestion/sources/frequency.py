"""Token-frequency source: per-lemma Zipf values from ``wordfreq`` (phase 6).

One isolated loader per dataset (the phase 5.5 Step 3 pattern), and the only
impure part of the frequency signal: it calls ``wordfreq`` and returns a plain
mapping the pure `ingestion.enrich` core consumes, so the enrichment math is
testable without the optional dependency.

Distinct from `ingestion.staging.frequency`, which stages a top-N
``(word, rank, zipf)`` list for the phase-5.54 exploration notebooks. That answers
"what are the most common words in this language"; this answers "how common is
*this* form", for arbitrary forms including the multiword ones a top-N list never
contains. Same library, different question, so both exist.

Two properties of ``wordfreq`` shape the contract, both measured on the real
corpus (2026-09-02):

- **An unknown form scores ``0.0``**, which is indistinguishable from "measured as
  never occurring". `lemma_zipf` maps it to ``None`` so absence stays absence;
  15-21% of our lemmas land there, per language.
- **A multiword form is composed, not measured.** ``wordfreq`` estimates a phrase
  from its components, and 20-44% of our lemmas are multiword. The value is still
  useful for ranking, so it is kept, but `is_composed` flags it and the enrichment
  marks those senses estimated.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version
from typing import TYPE_CHECKING

from loguru import logger as lg

from lang_tools.lexicon.ingestion.deps import OptionalDependencyMissingError

if TYPE_CHECKING:
    from collections.abc import Iterable

    from lang_tools.lexicon.lemma import Lemma

#: Characters that make a form multiword, so its ``wordfreq`` value is composed
#: from components rather than measured (see the module docstring).
_MULTIWORD_MARKERS = (" ", "_", "-")


def _require_wordfreq():  # noqa: ANN202 - the wordfreq module, kept lazy
    """Import ``wordfreq`` lazily, mapping absence to a clear error."""
    try:
        import wordfreq  # noqa: PLC0415 - lazy so the extra stays optional  # pyright: ignore[reportMissingImports]
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        package, extra = "wordfreq", "ingest"
        raise OptionalDependencyMissingError(package, extra) from exc
    return wordfreq


def is_composed(text: str) -> bool:
    """Report whether ``wordfreq`` composes this form's score, rather than measuring it.

    Args:
        text: A lemma surface form.

    Returns:
        True for multiword forms (space, underscore or hyphen separated).
    """
    return any(marker in text for marker in _MULTIWORD_MARKERS)


def lemma_zipf(lemmas: Iterable[Lemma]) -> dict[tuple[str, str], float]:
    """Return ``{(text, language): zipf}`` for every lemma with a known frequency.

    Zipf is ``wordfreq``'s log10 scale: 3.0 means one occurrence per million
    words. Forms ``wordfreq`` does not know are **omitted** rather than stored as
    ``0.0``, so a missing key means "no frequency", never "frequency zero".

    Args:
        lemmas: The lemmas to look up; duplicates are computed once.

    Returns:
        Mapping from ``(text, language)`` to the form's Zipf value.

    Raises:
        OptionalDependencyMissingError: When the ``ingest`` extra is not installed.
    """
    wordfreq = _require_wordfreq()
    scores: dict[tuple[str, str], float] = {}
    seen: set[tuple[str, str]] = set()
    for lemma in lemmas:
        key = (lemma.text, lemma.language)
        if key in seen:
            continue
        seen.add(key)
        zipf = wordfreq.zipf_frequency(lemma.text, lemma.language)
        if zipf > 0:
            scores[key] = zipf
    lg.info("Frequency lookup: {} of {} forms known", len(scores), len(seen))
    return scores


def wordfreq_version() -> str:
    """Return the installed ``wordfreq`` distribution version (or ``"unknown"``).

    Read from the package metadata, not from a ``__version__`` attribute:
    ``wordfreq`` does not define one, so the attribute lookup the staging adapter
    used to do always fell through to ``"unknown"``, and every staging manifest
    entry written since phase 5.54 records that. The version is a real pin - it
    selects the frequency data the build reads - so it has to come from somewhere
    that exists.

    Returns:
        The installed version string, or ``"unknown"`` when the distribution
        metadata is absent (e.g. a source tree on ``sys.path``).
    """
    try:
        return version("wordfreq")
    except PackageNotFoundError:  # pragma: no cover - installed in every env we run
        return "unknown"
