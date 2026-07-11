"""OMW (Open Multilingual Wordnet) source adapter - the concept backbone.

OMW's native unit *is* the concept we want: a synset is a language-independent
meaning, linked across languages by the Princeton interlingual index (ILI). This
module turns OMW synsets into our models in two clearly separated halves:

- `wn_synset_entries` does the **impure** part: it lazy-imports ``wn``, opens the
  per-language wordnets, and flattens each synset into a small `SynsetEntry`. It
  is the only place in this module that touches ``wn`` (the CILI gloss map is the
  sibling `cili` loader's job), so it is never exercised in unit tests.
- `group_to_records` does the **pure** part: it groups the flattened entries by
  their shared ILI key (this is the cross-lingual grouping that gives cognate
  clustering for free), builds `Concept` / `Lemma` / `Sense` models, and applies
  the CILI English-gloss fallback from a passed-in gloss map. It is fully
  deterministic and unit-tested with fake entries.

The split keeps the heavy ``wn`` dependency optional (the ``ingest`` extra) and
the mapping logic testable without any download. See
``scratch_space/09_concept_model/05_ingestion.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import TYPE_CHECKING

from loguru import logger as lg

from lang_tools.language.normalization import normalize
from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.concept_id import concept_id
from lang_tools.lexicon.lemma import Lemma
from lang_tools.lexicon.relations import ConceptRelation
from lang_tools.lexicon.sense import Sense

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Iterator
    from collections.abc import Mapping

#: Provenance tags this adapter emits (the on-disk `codec.PROVENANCE_COL` values).
#: A concept built from OMW glosses is ``omw``; one whose English gloss is the
#: CILI fallback (the gloss map comes from the sibling `cili` loader) is ``cili``.
#: Both are permissive. `transform` re-exports ``SOURCE_OMW`` and owns the rest.
SOURCE_OMW = "omw"
SOURCE_CILI = "cili"

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

#: Substrings that mark a member form as a wiki-derivation artifact (phase 5.55
#: Q4): URL-encoded Wikipedia section anchors ("Grotte#Culture",
#: "Radiateur#.C3.89changeur ...") and HTML-entity fragments ("c&amp;#339;..."),
#: all localized in the WOLF-derived omw-fr wordnet. Matched case-insensitively
#: (the dumps carry both ".C3." and ".c3.").
_MALFORMED_FORM_MARKERS = ("#", ".c3.")

#: Default OMW release version (the ``:1.4`` suffix on lexicon specifiers).
OMW_VERSION = "1.4"

#: ISO 639-1 -> OMW lexicon id (without the ``:version`` suffix). OMW lexicon ids
#: are not always ``omw-{iso}`` (``it`` has two wordnets - MultiWordNet
#: ``omw-it`` vs ItalWordNet ``omw-iwn``), so the mapping is explicit. Both
#: ``acquire.download_omw`` (download set) and `wn_synset_entries` (read set) go
#: through `_omw_lexicon`, so the two can never drift.
OMW_LEXICONS: dict[str, str] = {
    "en": "omw-en",
    "pt": "omw-pt",
    "es": "omw-es",
    "fr": "omw-fr",
    "it": "omw-it",  # MultiWordNet; deliberately not omw-iwn (ItalWordNet)
}


class UnknownOmwLanguageError(KeyError):
    """Raised when no OMW lexicon is mapped for a language code."""

    def __init__(self, language: str) -> None:
        """Initialize with the unsupported language code.

        Args:
            language: The ISO 639-1 code with no mapped OMW lexicon.
        """
        super().__init__(
            f"No OMW lexicon known for {language!r} "
            f"(known: {sorted(OMW_LEXICONS)}).",
        )
        self.language = language


def _omw_lexicon(lang: str, version: str = OMW_VERSION) -> str:
    """Return the versioned OMW lexicon specifier for a language.

    Args:
        lang: ISO 639-1 code (must be in `OMW_LEXICONS`).
        version: OMW release version appended as ``:version``.

    Returns:
        A single-lexicon specifier such as ``"omw-en:1.4"``.

    Raises:
        UnknownOmwLanguageError: When `lang` has no mapped lexicon.
    """
    try:
        base = OMW_LEXICONS[lang]
    except KeyError as exc:
        raise UnknownOmwLanguageError(lang) from exc
    return f"{base}:{version}"


def _ili_id(synset: object) -> str | None:
    """Normalize a ``wn`` synset's ILI to a plain id string or ``None``.

    In ``wn`` 1.1.0 ``Synset.ili`` is the interlingual-index id as a bare string
    (e.g. ``"i35545"``) or a falsy value when the synset has no ILI. Earlier/later
    ``wn`` could return an object exposing ``.id``; tolerate both shapes and map
    the empty case to ``None`` (the "monolingual, group by synset id" signal).
    """
    raw_ili = getattr(synset, "ili", None)
    return getattr(raw_ili, "id", raw_ili) or None


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


def is_malformed_form(form: str) -> bool:
    """Report whether a member form is a wiki-derivation artifact to drop.

    Phase 5.55 Q4 decision: forms containing a Wikipedia section anchor or a
    URL-encoding fragment (`_MALFORMED_FORM_MARKERS`) are malformed tokens, not
    words - `group_to_records` drops them (and their would-be senses) instead of
    minting lemmas. The concept itself is kept; its other members still attach.

    Args:
        form: A member lemma form as read from the wordnet.

    Returns:
        True when the form matches a malformed-form marker.
    """
    lowered = form.lower()
    return any(marker in lowered for marker in _MALFORMED_FORM_MARKERS)


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
        lexfile: WordNet lexicographer class (e.g. ``"noun.motion"``), if any.
            Concept-level: present on the English synset, shared via the ILI.
        examples: The synset's example sentences in `language` (concept-level).
        hypernyms: Lexicon-local synset ids this synset points to as hypernyms
            (same wordnet, so same `language`). Resolved to `ConceptRelation`
            edges in `group_to_records`; hyponymy is the same edge read in
            reverse, so it is not stored separately.
    """

    language: str
    synset_id: str
    ili: str | None
    definition: str | None
    lemmas: tuple[str, ...]
    pos: str | None = None
    lexfile: str | None = None
    examples: tuple[str, ...] = ()
    hypernyms: tuple[str, ...] = ()


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


def _tiered_slugs(grouped: Mapping[str, list[SynsetEntry]]) -> dict[str, str]:
    """Compute the final slug per grouping key with the 5.55 tier-0/1 scheme.

    Tier 0: the `_pick_slug_source` slug; kept when unique across the build.
    Tier 1: when the tier-0 slug collides (or is the generic ``"concept"``
    fallback), append the concept's slugified lexfile as a deterministic
    discriminant (``cut`` -> ``cut-noun-act`` vs ``cut-verb-contact``). Groups
    that still collide after tier 1 (same slug *and* same lexfile - true
    polysemy) keep the tier-1 slug; the id hash carries uniqueness regardless,
    and the LLM qualifier tier is deferred to phase 8.

    Args:
        grouped: The grouping-key -> entries map built by `group_to_records`.

    Returns:
        ``{grouping_key: final_slug}`` for every group.
    """
    base_slugs = {
        key: slugify(_pick_slug_source(group)) for key, group in grouped.items()
    }
    counts: dict[str, int] = {}
    for slug in base_slugs.values():
        counts[slug] = counts.get(slug, 0) + 1
    slugs: dict[str, str] = {}
    for key, base in base_slugs.items():
        if counts[base] > 1 or base == "concept":
            lexfile = _pick_lexfile(grouped[key])
            if lexfile:
                slugs[key] = f"{base}-{slugify(lexfile)}"
                continue
        slugs[key] = base
    return slugs


def _pick_lexfile(group: list[SynsetEntry]) -> str | None:
    """Return the concept's lexfile, preferring the English synset's.

    lexfile is carried on the English/ILI synset (phase 5.54 Topic 2); the group
    shares an ILI, so the English entry's lexfile is the concept's. Falls back to
    any member's lexfile so an English-excluded build still gets one where present.
    """
    for entry in group:
        if entry.language == "en" and entry.lexfile:
            return entry.lexfile
    for entry in group:
        if entry.lexfile:
            return entry.lexfile
    return None


def _group_definitions(
    group: list[SynsetEntry],
    glosses: Mapping[str, str],
) -> tuple[dict[str, str], str]:
    """Collect a concept's per-language definitions and its provenance tag.

    One definition per language; the first non-empty gloss wins. When the group
    has no English gloss, the CILI fallback (keyed by the group's ILI id) fills
    the en slot and tags the concept `SOURCE_CILI`; see the English-gloss policy
    in `group_to_records`.

    Returns:
        The definitions map and the concept's source tag (omw or cili).
    """
    definitions: dict[str, str] = {}
    for entry in group:
        if entry.definition and entry.language not in definitions:
            definitions[entry.language] = entry.definition
    source = SOURCE_OMW
    if "en" not in definitions and glosses:
        group_ili = next((e.ili for e in group if e.ili), None)
        gloss = glosses.get(group_ili) if group_ili else None
        if gloss:
            definitions["en"] = gloss
            source = SOURCE_CILI
    return definitions, source


def _group_examples(group: list[SynsetEntry]) -> dict[str, list[str]]:
    """Collect a concept's example sentences per language (sorted, de-duplicated).

    OMW examples live on the synset, so they are concept-level; each entry carries
    them in its own language. Sorting + de-duping keeps the output deterministic
    (the persisted shape must be byte-stable). Languages with no example are
    omitted rather than stored empty.
    """
    by_lang: dict[str, set[str]] = {}
    for entry in group:
        for example in entry.examples:
            if example:
                by_lang.setdefault(entry.language, set()).add(example)
    return {lang: sorted(examples) for lang, examples in sorted(by_lang.items())}


def _hypernym_edges(
    grouped: Mapping[str, list[SynsetEntry]],
    key_to_cid: Mapping[tuple[str, str], str],
) -> tuple[list[ConceptRelation], int]:
    """Resolve OMW hypernym links to deduped, sorted `ConceptRelation` edges.

    Each ``hypernym`` target is a lexicon-local synset id in the same language, so
    it resolves through `key_to_cid` (built from every ingested synset). An edge is
    directional: ``concept_id_a`` is the more specific child, ``concept_id_b`` its
    hypernym (the parent); hyponymy is this edge read in reverse, so it is not
    stored separately. A target that does not resolve (filtered out / cross-lexicon)
    is counted as dangling and dropped, never emitted as a half edge.

    Returns:
        The sorted unique hypernym edges and the dropped-dangling-edge count.
    """
    edges: set[tuple[str, str]] = set()
    dangling = 0
    for group in grouped.values():
        for entry in group:
            child = key_to_cid.get((entry.language, entry.synset_id))
            if child is None:  # pragma: no cover - the entry is always in the map
                continue
            for target in entry.hypernyms:
                parent = key_to_cid.get((entry.language, target))
                if parent is None:
                    dangling += 1
                elif parent != child:  # OMW never self-links; guard anyway
                    edges.add((child, parent))
    relations = [
        ConceptRelation(concept_id_a=a, concept_id_b=b, relation_type="hypernym")
        for a, b in sorted(edges)
    ]
    return relations, dangling


def group_to_records(
    entries: Iterable[SynsetEntry],
    cili_glosses: Mapping[str, str] | None = None,
) -> tuple[list[Concept], list[Lemma], list[Sense], list[str], list[ConceptRelation]]:
    """Group flattened synset entries by ILI into concept/lemma/sense models.

    All entries that share an ILI become **one** `Concept` whose `definitions`
    map holds the per-language glosses; every member lemma of every language in
    the group becomes a thin `Lemma` and an attaching `Sense` edge. Lemmas are
    de-duplicated by `Lemma.id` (a form shared by two synsets is one token);
    senses are de-duplicated by ``(lemma_id, concept_id)``. Member forms that
    match `is_malformed_form` (wiki-anchor artifacts, phase 5.55 Q4) are dropped
    with their would-be senses and counted in the log.

    Slug policy (phase 5.55 work item A): slugs are tiered via `_tiered_slugs` -
    the tier-0 `_pick_slug_source` slug when unique, else the slugified lexfile
    appended as a deterministic tier-1 discriminant. Only the id's slug half
    changes; the hash half stays keyed on the grouping key.

    English-gloss policy (phase 5.5 Step 2): when OMW left a concept's English
    gloss blank, fall back to the permissive CILI gloss for the concept's ILI id
    (`cili_glosses`, from the separate `cili` loader). Such a concept is tagged
    `SOURCE_CILI`; everything else is `SOURCE_OMW`. The fallback is keyed by ILI
    id (a precise concept-level key), so it never attaches a gloss to a concept it
    cannot identify. It is dormant for English-inclusive OMW builds (an ILI
    implies a Princeton/English synset, and `omw-en` has ~100% gloss coverage) -
    verified 0 hits on the en/pt/es/fr/it build; kept for English-excluded builds.
    Non-English glosses are OMW-only and stay empty when OMW has none.

    Args:
        entries: The flattened synset entries (from `wn_synset_entries` or fakes).
        cili_glosses: Optional ``{ili_id: english_gloss}`` map (the `cili` loader's
            output), consulted only to fill a missing English gloss. ``None``
            disables the fallback (every concept stays `SOURCE_OMW`).

    Phase 5.5 Step 4 fields, all concept-level (ILI-keyed, so they propagate):
    each concept also gets its `lexfile` (from the English synset, see
    `_pick_lexfile`) and per-language `examples` (from the synset, see
    `_group_examples`), and the OMW ``hypernym`` links become directional
    `ConceptRelation` edges (see `_hypernym_edges`). A hypernym target that does
    not resolve to a concept is dropped and logged, never emitted half-formed.

    Returns:
        The concepts, lemmas, senses (each sorted by id for determinism), the
        per-concept provenance tag list parallel to the sorted concepts, and the
        sorted unique hypernym `ConceptRelation` edges.
    """
    glosses = cili_glosses or {}
    grouped: dict[str, list[SynsetEntry]] = {}
    for entry in entries:
        grouped.setdefault(_grouping_key(entry), []).append(entry)

    slugs = _tiered_slugs(grouped)
    concepts: list[Concept] = []
    concept_source_by_id: dict[str, str] = {}
    lemmas: dict[str, Lemma] = {}
    senses: dict[tuple[str, str], Sense] = {}
    key_to_cid: dict[tuple[str, str], str] = {}
    malformed_dropped = 0

    for key, group in grouped.items():
        cid = concept_id(slugs[key], key)
        definitions, source = _group_definitions(group, glosses)
        concepts.append(
            Concept(
                id=cid,
                definitions=definitions,
                lexfile=_pick_lexfile(group),
                examples=_group_examples(group),
            ),
        )
        concept_source_by_id[cid] = source

        for entry in group:
            key_to_cid[(entry.language, entry.synset_id)] = cid
            pos = _POS_LABELS.get(entry.pos or "")
            for form in entry.lemmas:
                if is_malformed_form(form):
                    malformed_dropped += 1
                    continue
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

    relations, dangling = _hypernym_edges(grouped, key_to_cid)
    if dangling:
        lg.info("Dropped {} hypernym edge(s) with an unresolved target", dangling)
    if malformed_dropped:
        lg.info("Dropped {} malformed member form(s) (5.55 Q4)", malformed_dropped)

    concepts.sort(key=lambda c: c.id)
    sorted_lemmas = sorted(lemmas.values(), key=lambda lem: lem.id)
    sorted_senses = sorted(senses.values(), key=lambda s: s.id)
    concept_sources = [concept_source_by_id[c.id] for c in concepts]
    return concepts, sorted_lemmas, sorted_senses, concept_sources, relations


def wn_synset_entries(
    langs: Iterable[str],
    *,
    data_dir: str | None = None,
    omw_version: str = OMW_VERSION,
) -> Iterator[SynsetEntry]:
    """Yield `SynsetEntry` records from the installed OMW wordnets (lazy ``wn``).

    This is the only function that imports ``wn``; it is kept thin so the pure
    `group_to_records` carries all the mappable logic. ``wn`` must already have
    the wordnets downloaded (see `acquire.download_omw`).

    The reader selects by **lexicon**, not ``lang=``: a bare ``lang`` filter can
    match more than one installed wordnet (``it`` matches both ``omw-it`` and
    ``omw-iwn``) and silently merge them, making the build non-deterministic.
    Driving from `_omw_lexicon` pins each language to exactly one wordnet.

    Args:
        langs: ISO 639-1 codes to read (e.g. ``["en", "pt"]``). Each maps to a
            single OMW lexicon via `OMW_LEXICONS`.
        data_dir: Optional override for ``wn``'s data directory; ``None`` uses
            its default (``~/.wn_data``).
        omw_version: OMW release version used to build the lexicon specifiers.

    Yields:
        One `SynsetEntry` per (synset, language).

    Raises:
        IngestDependencyMissingError: When the ``ingest`` extra (``wn``) is not
            installed.
        UnknownOmwLanguageError: When a language has no mapped OMW lexicon.
    """
    wn = _require_wn()
    if data_dir is not None:
        wn.config.data_directory = data_dir  # pyright: ignore[reportPrivateImportUsage]
    for language in langs:
        spec = _omw_lexicon(language, omw_version)
        wordnet = wn.Wordnet(lexicon=spec)
        for synset in wordnet.synsets():
            yield SynsetEntry(
                language=language,
                synset_id=synset.id,
                ili=_ili_id(synset),
                definition=synset.definition(),
                lemmas=tuple(synset.lemmas()),
                pos=synset.pos,
                lexfile=synset.lexfile(),
                examples=tuple(synset.examples()),
                hypernyms=tuple(h.id for h in synset.hypernyms()),
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
