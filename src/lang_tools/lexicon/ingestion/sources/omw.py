"""OMW (Open Multilingual Wordnet) source adapter - the concept backbone.

OMW's native unit *is* the concept we want: a synset is a language-independent
meaning, linked across languages by the Princeton interlingual index (ILI). This
module turns OMW synsets into our models in two clearly separated halves:

- `wn_synset_entries` does the **impure** part: it lazy-imports ``wn``, opens the
  per-language wordnets, and flattens each synset into a small `SynsetEntry`. It
  is the only place that touches ``wn``, so it is never exercised in unit tests.
- `group_to_records` does the **pure** part: it groups the flattened entries by
  their shared ILI key (this is the cross-lingual grouping that gives cognate
  clustering for free) and builds `Concept` / `Lemma` / `Sense` models. It is
  fully deterministic and unit-tested with fake entries.

The split keeps the heavy ``wn`` dependency optional (the ``ingest`` extra) and
the mapping logic testable without any download. See
``scratch_space/09_concept_model/05_ingestion.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import TYPE_CHECKING

from lang_tools.language.normalization import normalize
from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.concept_id import concept_id
from lang_tools.lexicon.lemma import Lemma
from lang_tools.lexicon.sense import Sense

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Iterator

#: WordNet single-letter part-of-speech codes -> our labels.
_POS_LABELS: dict[str, str] = {
    "n": "noun",
    "v": "verb",
    "a": "adjective",
    "s": "adjective",  # "satellite" adjective
    "r": "adverb",
}

#: How many slug words to keep, so concept ids stay short but legible.
_SLUG_WORDS = 4


def slugify(text: str) -> str:
    """Return a lowercase, hyphenated, accent-free slug for a concept id.

    Matches the ``[a-z0-9-]+`` slug shape that `concept_id` / `CONCEPT_ID_RE`
    require. Empty / punctuation-only input yields ``"concept"`` so a slug is
    always producible (the hash suffix carries uniqueness regardless).

    Args:
        text: Any human string (a lemma or the start of a gloss).

    Returns:
        A non-empty slug of at most `_SLUG_WORDS` words.
    """
    cleaned = re.sub(r"[^a-z0-9]+", "-", normalize(text)).strip("-")
    if not cleaned:
        return "concept"
    return "-".join(cleaned.split("-")[:_SLUG_WORDS])


@dataclass(frozen=True)
class SynsetEntry:
    """One OMW synset flattened for one language (the pure intermediate shape).

    Attributes:
        language: ISO 639-1 code of the wordnet this synset came from.
        synset_id: The lexicon-local synset id (the fallback grouping key).
        ili: The interlingual index id shared across languages, or ``None`` when
            the synset has no ILI (then it groups by `synset_id` alone, i.e. it
            stays monolingual).
        definition: The synset gloss in `language`, if any.
        lemmas: The synset's member lemma forms in `language`.
        pos: WordNet part-of-speech code (``"n"``, ``"v"``, ...), if any.
    """

    language: str
    synset_id: str
    ili: str | None
    definition: str | None
    lemmas: tuple[str, ...]
    pos: str | None = None


def _grouping_key(entry: SynsetEntry) -> str:
    """Return the cross-lingual grouping key for an entry (ILI, else synset id)."""
    if entry.ili:
        return f"ili::{entry.ili}"
    return f"syn::{entry.language}::{entry.synset_id}"


def _pick_slug_source(group: list[SynsetEntry]) -> str:
    """Pick the most legible base string for a concept's slug.

    Prefers an English lemma, then any lemma, then the start of any definition,
    so ids read like ``c__house__<hash>`` rather than ``c__concept__<hash>``.
    """
    for entry in group:
        if entry.language == "en" and entry.lemmas:
            return entry.lemmas[0]
    for entry in group:
        if entry.lemmas:
            return entry.lemmas[0]
    for entry in group:
        if entry.definition:
            return entry.definition
    return "concept"


def group_to_records(
    entries: Iterable[SynsetEntry],
) -> tuple[list[Concept], list[Lemma], list[Sense]]:
    """Group flattened synset entries by ILI into concept/lemma/sense models.

    All entries that share an ILI become **one** `Concept` whose `definitions`
    map holds the per-language glosses; every member lemma of every language in
    the group becomes a thin `Lemma` and an attaching `Sense` edge. Lemmas are
    de-duplicated by `Lemma.id` (a form shared by two synsets is one token);
    senses are de-duplicated by ``(lemma_id, concept_id)``.

    Args:
        entries: The flattened synset entries (from `wn_synset_entries` or fakes).

    Returns:
        The concepts, lemmas, and senses, each sorted by id for determinism.
    """
    grouped: dict[str, list[SynsetEntry]] = {}
    for entry in entries:
        grouped.setdefault(_grouping_key(entry), []).append(entry)

    concepts: list[Concept] = []
    lemmas: dict[str, Lemma] = {}
    senses: dict[tuple[str, str], Sense] = {}

    for key, group in grouped.items():
        slug = slugify(_pick_slug_source(group))
        cid = concept_id(slug, key)
        # One definition per language; the first non-empty gloss wins.
        definitions: dict[str, str] = {}
        for entry in group:
            if entry.definition and entry.language not in definitions:
                definitions[entry.language] = entry.definition
        concepts.append(Concept(id=cid, definitions=definitions))

        for entry in group:
            pos = _POS_LABELS.get(entry.pos or "")
            for form in entry.lemmas:
                lemma = Lemma(
                    text=form,
                    language=entry.language,
                    part_of_speech=pos,
                    sources=["omw"],
                )
                lemmas.setdefault(lemma.id, lemma)
                senses.setdefault(
                    (lemma.id, cid),
                    Sense(lemma_id=lemma.id, concept_id=cid),
                )

    concepts.sort(key=lambda c: c.id)
    sorted_lemmas = sorted(lemmas.values(), key=lambda lem: lem.id)
    sorted_senses = sorted(senses.values(), key=lambda s: s.id)
    return concepts, sorted_lemmas, sorted_senses


def wn_synset_entries(
    langs: Iterable[str],
    *,
    data_dir: str | None = None,
) -> Iterator[SynsetEntry]:
    """Yield `SynsetEntry` records from the installed OMW wordnets (lazy ``wn``).

    This is the only function that imports ``wn``; it is kept thin so the pure
    `group_to_records` carries all the mappable logic. ``wn`` must already have
    the wordnets downloaded (see `acquire.download_omw`).

    Args:
        langs: ISO 639-1 codes to read (e.g. ``["en", "pt"]``). Each maps to the
            OMW lexicon installed for that language.
        data_dir: Optional override for ``wn``'s data directory; ``None`` uses
            its default (``~/.wn_data``).

    Yields:
        One `SynsetEntry` per (synset, language).

    Raises:
        IngestDependencyMissingError: When the ``ingest`` extra (``wn``) is not
            installed.
    """
    wn = _require_wn()
    if data_dir is not None:
        wn.config.data_directory = data_dir
    for language in langs:
        wordnet = wn.Wordnet(lang=language)
        for synset in wordnet.synsets():
            ili = synset.ili
            yield SynsetEntry(
                language=language,
                synset_id=synset.id,
                ili=ili.id if ili is not None else None,
                definition=synset.definition(),
                lemmas=tuple(synset.lemmas()),
                pos=synset.pos,
            )


class IngestDependencyMissingError(ImportError):
    """Raised when the OMW download/read path is used without the ``ingest`` extra."""

    def __init__(self) -> None:
        """Initialize with install guidance."""
        super().__init__(
            "OMW ingestion needs the 'ingest' extra (wn). Install it with "
            "`uv sync --extra ingest`.",
        )


def _require_wn():  # noqa: ANN202 - the wn module, kept lazy
    """Import ``wn`` lazily, mapping absence to a clear error."""
    try:
        import wn  # noqa: PLC0415 - lazy so the extra stays optional  # pyright: ignore[reportMissingImports]
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise IngestDependencyMissingError from exc
    return wn
