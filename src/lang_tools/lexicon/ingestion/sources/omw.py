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

from collections import Counter
from dataclasses import dataclass
from dataclasses import field
import html
import re
from typing import TYPE_CHECKING
from typing import Any

from loguru import logger as lg

from lang_tools.language.normalization import normalize
from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.concept_id import concept_id
from lang_tools.lexicon.concept_id import source_key_hash
from lang_tools.lexicon.ingestion.deps import OptionalDependencyMissingError
from lang_tools.lexicon.lemma import Lemma
from lang_tools.lexicon.lemma_id import lemma_id
from lang_tools.lexicon.relations import RELATION_ANTONYM
from lang_tools.lexicon.relations import RELATION_HYPERNYM
from lang_tools.lexicon.relations import SYMMETRIC_CONCEPT_RELATIONS
from lang_tools.lexicon.relations import ConceptRelation
from lang_tools.lexicon.relations import SenseRelation
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
#: Provenance of a concept edge the source does not state but implies: the
#: concept-level ``antonym`` edges lifted from English sense antonymy (phase 7).
SOURCE_DERIVED = "derived"

#: ``wn`` synset relation name -> ``(stored type, reverse the endpoints?)``.
#: Phase 7: each WordNet inverse pair is stored in one direction, and both of its
#: names are read, so a lexicon that states a link from only one side still
#: contributes it. OMW 1.4's English mirrors every pair but one link; the rule
#: costs nothing there and does not assume it of any other source. Names absent
#: here (``domain_*``, ``exemplifies``, ...) are deferred and never read. See
#: `relations.DIRECTIONAL_CONCEPT_RELATIONS` for what each stored orientation
#: means.
SYNSET_RELATIONS: dict[str, tuple[str, bool]] = {
    "hypernym": (RELATION_HYPERNYM, False),
    "hyponym": (RELATION_HYPERNYM, True),
    "instance_hypernym": ("instance_hypernym", False),
    "instance_hyponym": ("instance_hypernym", True),
    "mero_member": ("mero_member", False),
    "holo_member": ("mero_member", True),
    "mero_part": ("mero_part", False),
    "holo_part": ("mero_part", True),
    "mero_substance": ("mero_substance", False),
    "holo_substance": ("mero_substance", True),
    "entails": ("entails", False),  # no inverse type occurs in OMW 1.4
    "causes": ("causes", False),  # no inverse type occurs in OMW 1.4
    "similar": ("similar", False),  # symmetric: canonical order makes direction moot
    "also": ("also", False),
    "attribute": ("attribute", False),
}

#: ``wn`` sense relation names read into `SenseRelation` edges. Only English has
#: any sense relations at all; ``derivation`` / ``pertainym`` are deferred.
SENSE_RELATIONS: frozenset[str] = frozenset({RELATION_ANTONYM})

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
#: "Radiateur#.C3.89changeur ...") and, after `unescape_form` has resolved the
#: HTML entities, leftover markup ("Milan <!--gender?-->", "vitamine B<sub>6</sub>",
#: pt "<HTML>"). Matched case-insensitively (the dumps carry both ".C3." and
#: ".c3."). No legitimate member form in the five wordnets contains "<".
_MALFORMED_FORM_MARKERS = ("#", ".c3.", "<")

#: Member forms that are placeholders rather than words, matched exactly and
#: case-insensitively (phase 5.57). MultiWordNet writes these into the Italian
#: wordnet to mark a synset it has no Italian lexicalization for; they reached
#: the corpus as ordinary it noun lemmas on 1,008 concepts. Exact match matters:
#: en "gap" and pt "Gap" are legitimate lemmas.
_PLACEHOLDER_FORMS = frozenset({"gap!", "pseudogap!"})

#: Cap on `unescape_form`'s fixed-point loop. The corpus needs two passes (the
#: doubly-escaped "fr&amp;eacute;n&amp;eacute;sie"); the cap only exists so a
#: crafted input cannot spin.
_UNESCAPE_MAX_PASSES = 3

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


def unescape_form(form: str) -> str:
    """Resolve HTML entities in a member form (phase 5.57).

    A handful of WOLF-derived French forms reach the dump HTML-escaped. Some are
    recoverable words once unescaped ("fr&amp;eacute;n&amp;eacute;sie" ->
    "frénésie", which merges into the lemma that already exists); the rest turn
    into plain markup that `is_malformed_form` then drops. Running this first
    means the two cases are handled by repair and by drop respectively, instead
    of both being thrown away.

    Some forms are escaped twice ("&amp;eacute;" needs two passes), so this
    unescapes to a fixed point, bounded by `_UNESCAPE_MAX_PASSES` so a
    pathological input cannot loop.

    Args:
        form: A member lemma form as read from the wordnet.

    Returns:
        The form with HTML entities resolved; unchanged when it has none.
    """
    for _ in range(_UNESCAPE_MAX_PASSES):
        unescaped = html.unescape(form)
        if unescaped == form:
            break
        form = unescaped
    return form


#: Separators WOLF uses to join variant forms into one member: ``;`` ("maire ;
#: bourgmestre", 18 French forms) and ``|`` ("bail|bau|baux", 56 forms). Each
#: segment is a form of its own.
_VARIANT_SEPARATORS = re.compile(r"[;|]")

#: A ``|`` segment carrying a language tag ("lt=vaistutis", "fr: carnivore"):
#: an inline translation pasted in from Wiktionary, not a variant.
_TAGGED_SEGMENT = re.compile(r"^([a-z]{2,3})\s*[=:]\s*(.+)$")


def member_forms(raw_form: str, language: str = "") -> tuple[list[str], int]:
    """Clean one raw member form into the forms to keep (phase 8).

    Unescapes HTML entities (`unescape_form`), splits ``;`` / ``|``-joined
    variants into separate forms, keeps a language-tagged segment
    (``fr:carnivore``) only when its tag is `language` - the others are
    translations into other languages - de-duplicates, and drops what
    `is_malformed_form` rejects.

    Args:
        raw_form: A member form exactly as the wordnet stores it.
        language: ISO 639-1 code of the wordnet the form came from.

    Returns:
        The forms to keep, and how many were dropped as malformed.
    """
    kept: list[str] = []
    dropped = 0
    for part in _VARIANT_SEPARATORS.split(unescape_form(raw_form)):
        form = part.strip()
        tagged = _TAGGED_SEGMENT.match(form)
        if tagged:
            if tagged.group(1) != language:
                continue
            form = tagged.group(2).strip()
        if not form or form in kept:
            continue
        if is_malformed_form(form):
            dropped += 1
            continue
        kept.append(form)
    return kept, dropped


#: Order that breaks a part-of-speech tie between a lemma's synsets.
_POS_ORDER = ("noun", "verb", "adjective", "adverb")


class _LemmaTally:
    """Collect every surface variant and part of speech a lemma id is seen with.

    Lemma identity is case- and accent-insensitive (`lemma_id`), so one lemma
    can be met as ``be`` in thirteen synsets and as ``Be`` (beryllium) in one, and
    as a noun before it is met as a verb. Taking whichever came first made the
    verb *be* display as ``Be`` and *go* a noun (phase 8: 4,198 lemmas had a POS
    that was not their majority). `settle` picks the majority instead.
    """

    def __init__(self) -> None:
        self.forms: dict[str, Counter[str]] = {}
        self.pos: dict[str, Counter[str]] = {}

    def add(self, lemma_id_: str, form: str, pos: str | None) -> None:
        """Record one sighting of a lemma."""
        self.forms.setdefault(lemma_id_, Counter())[form] += 1
        if pos:
            self.pos.setdefault(lemma_id_, Counter())[pos] += 1

    def settle(self, lemma: Lemma) -> Lemma:
        """Return `lemma` with its majority text and part of speech.

        Text: the variant seen in the most synsets; a tie goes to the lowercase
        variant, then alphabetical order. POS: the most frequent; a tie follows
        `_POS_ORDER`. Every variant normalizes to the same id, so the id holds.
        """
        forms = self.forms[lemma.id]
        text = min(forms, key=lambda f: (-forms[f], f != f.lower(), f))
        pos_counts = self.pos.get(lemma.id)
        pos = (
            min(
                pos_counts,
                key=lambda p: (
                    -pos_counts[p],
                    _POS_ORDER.index(p) if p in _POS_ORDER else len(_POS_ORDER),
                ),
            )
            if pos_counts
            else lemma.part_of_speech
        )
        if text == lemma.text and pos == lemma.part_of_speech:
            return lemma
        return lemma.model_copy(update={"text": text, "part_of_speech": pos})


def is_malformed_form(form: str) -> bool:
    """Report whether a member form is a non-word token to drop.

    Phase 5.55 Q4 decision: forms containing a Wikipedia section anchor or a
    URL-encoding fragment (`_MALFORMED_FORM_MARKERS`) are malformed tokens, not
    words - `group_to_records` drops them (and their would-be senses) instead of
    minting lemmas. The concept itself is kept; its other members still attach.
    Phase 5.57 extends this to leftover HTML markup (via the ``"<"`` marker, on
    forms already passed through `unescape_form`) and to MultiWordNet's
    placeholder forms (`_PLACEHOLDER_FORMS`), which mark a synset as having no
    lexicalization in that language rather than naming a word.

    Args:
        form: A member lemma form, already unescaped.

    Returns:
        True when the form is a placeholder or matches a malformed-form marker.
    """
    lowered = form.lower()
    if lowered.strip() in _PLACEHOLDER_FORMS:
        return True
    return any(marker in lowered for marker in _MALFORMED_FORM_MARKERS)


@dataclass(frozen=True)
class SenseLink:
    """One sense-level relation read off a synset member (the pure shape).

    Attributes:
        form: The member form of *this* synset the link starts from.
        relation_type: The ``wn`` sense relation name (in `SENSE_RELATIONS`).
        target_synset_id: Lexicon-local id of the target sense's synset.
        target_form: The member form of the target sense.
    """

    form: str
    relation_type: str
    target_synset_id: str
    target_form: str


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
        member_counts: SemCor sense-tag counts parallel to `lemmas` (same length
            and order), or an empty tuple when the source carries none. Only the
            English wordnet has them - a 5,000-sense sample of ``omw-it:1.4``
            carries zero, matching phase 5.54 Topic 3's finding - so this is the
            English-only per-sense signal phase 6 sums to concept commonness and
            uses to split token frequency across senses.
        pos: WordNet part-of-speech code (``"n"``, ``"v"``, ...), if any.
        lexfile: WordNet lexicographer class (e.g. ``"noun.motion"``), if any.
            Concept-level: present on the English synset, shared via the ILI.
        examples: The synset's example sentences in `language` (concept-level).
        relations: ``wn`` relation name -> lexicon-local target synset ids (same
            wordnet, so same `language`), for the names in `SYNSET_RELATIONS`.
            Resolved to normalized `ConceptRelation` edges in `group_to_records`.
        sense_links: Sense-level relations of this synset's members (antonymy),
            resolved to `SenseRelation` edges in `group_to_records`.
        domain_topics: English names of the synset's OMW ``domain_topic``
            targets (``"music"``, ``"law"``, ...). Not a stored relation: the
            topic stage maps the few a learner would browse by onto topics.
    """

    language: str
    synset_id: str
    ili: str | None
    definition: str | None
    lemmas: tuple[str, ...]
    member_counts: tuple[int, ...] = ()
    pos: str | None = None
    lexfile: str | None = None
    examples: tuple[str, ...] = ()
    relations: dict[str, tuple[str, ...]] = field(default_factory=dict)
    sense_links: tuple[SenseLink, ...] = ()
    domain_topics: tuple[str, ...] = ()


#: Language whose wordnet carries SemCor sense-tag counts. Only the English
#: lexicon has them (phase 5.54 Topic 3), and phase 6 propagates the resulting
#: concept-level signal to the other languages through the shared ILI.
COUNT_LANGUAGE = "en"


def _forms_with_counts(entry: SynsetEntry) -> Iterator[tuple[str, int]]:
    """Pair each member form with its SemCor count (0 when the source has none).

    `SynsetEntry.member_counts` is either empty or exactly parallel to `lemmas`;
    a short tuple would silently mis-attribute counts to the wrong forms, so it
    is rejected rather than zip-truncated.

    Args:
        entry: The synset entry whose members to pair.

    Yields:
        ``(form, count)`` in member order.

    Raises:
        MemberCountMismatchError: When `member_counts` is neither empty nor the
            same length as `lemmas`.
    """
    if not entry.member_counts:
        for form in entry.lemmas:
            yield form, 0
        return
    if len(entry.member_counts) != len(entry.lemmas):
        raise MemberCountMismatchError(entry)
    yield from zip(entry.lemmas, entry.member_counts, strict=True)


class MemberCountMismatchError(ValueError):
    """Raised when a `SynsetEntry`'s SemCor counts do not match its member forms."""

    def __init__(self, entry: SynsetEntry) -> None:
        """Initialize with the offending entry's shape.

        Args:
            entry: The entry whose `member_counts` is misaligned.
        """
        super().__init__(
            f"{entry.language}/{entry.synset_id}: got {len(entry.member_counts)} "
            f"member counts for {len(entry.lemmas)} member forms (they must be "
            "parallel, or the counts empty).",
        )
        self.entry = entry


@dataclass(frozen=True)
class GroupedRecords:
    """Everything `group_to_records` produces from one pass over the entries.

    Phase 6 replaced a five-element tuple with this: the SemCor counts made it a
    seventh positional element, and three call sites already unpacked it by
    position, where a mis-ordered unpack would be silent.

    Attributes:
        concepts: The grouped concepts, sorted by id.
        lemmas: The de-duplicated member lemmas, sorted by id.
        senses: The lemma <-> concept edges, sorted by id.
        concept_sources: Provenance tags parallel to `concepts`.
        relations: Sorted unique `ConceptRelation` edges: the normalized synset
            relations plus the concept antonyms derived from sense antonymy.
        relation_sources: Provenance tags parallel to `relations` (`SOURCE_OMW`
            for read edges, `SOURCE_DERIVED` for the derived antonyms).
        sense_relations: Sorted unique `SenseRelation` edges (antonymy).
        concept_domains: ``{concept_id: {domain name, ...}}`` gathered from the
            group's `SynsetEntry.domain_topics`, for the topic stage. Only
            concepts with a domain are present.
        qualifiers_applied: Concepts whose slug took a tier-2 qualifier.
        sense_counts: ``{(lemma_id, concept_id): semcor_count}`` for the senses
            that carry one. Sparse by nature (English only, and 17% of English
            senses), so absence means "no count", never "counted zero".
        concept_counts: ``{concept_id: semcor_total}`` summed over the concept's
            English senses. Present with value ``0`` for a concept that has an
            English member SemCor never tagged; **absent** for a concept with no
            English member at all. Phase 6's `Concept.commonness` keeps those two
            apart (``0.0`` vs ``None``), so the distinction has to survive here.
    """

    concepts: list[Concept]
    lemmas: list[Lemma]
    senses: list[Sense]
    concept_sources: list[str]
    relations: list[ConceptRelation]
    relation_sources: list[str]
    sense_relations: list[SenseRelation]
    concept_domains: dict[str, set[str]]
    sense_counts: dict[tuple[str, str], int]
    concept_counts: dict[str, int]
    qualifiers_applied: int = 0


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


def _tiered_slugs(
    grouped: Mapping[str, list[SynsetEntry]],
    qualifiers: Mapping[str, str] | None = None,
) -> tuple[dict[str, str], int]:
    """Compute the final slug per grouping key with the 5.55 + phase-8 tiers.

    Tier 0: the `_pick_slug_source` slug; kept when unique across the build.
    Tier 1: when the tier-0 slug collides (or is the generic ``"concept"``
    fallback), append the concept's slugified lexfile as a deterministic
    discriminant (``cut`` -> ``cut-noun-act`` vs ``cut-verb-contact``).
    Tier 2 (phase 8): a concept whose tier-1 slug still collides (same slug *and*
    same lexfile - true polysemy) takes its curated qualifier, if one was
    accepted, keyed by the grouping key's hash (`source_key_hash`, the half of the
    id a re-slug never changes). See `_qualified_slugs`. Anything left colliding
    keeps its tier-1 slug; the id hash carries uniqueness regardless.

    Args:
        grouped: The grouping-key -> entries map built by `group_to_records`.
        qualifiers: Accepted tier-2 qualifiers, ``{key hash: qualifier}``.

    Returns:
        ``{grouping_key: final_slug}`` for every group, and how many groups took
        a tier-2 qualifier.
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
    if not qualifiers:
        return slugs, 0
    return _qualified_slugs(slugs, base_slugs, qualifiers)


def _qualified_slugs(
    tier1: dict[str, str],
    base_slugs: Mapping[str, str],
    qualifiers: Mapping[str, str],
) -> tuple[dict[str, str], int]:
    """Apply tier-2 qualifiers to the still-colliding tier-1 slugs.

    Each colliding key with a qualifier ``q`` tries, in order: ``{base}-{q}``
    (shortest, e.g. ``hot-stolen-smuggled``), then ``{tier1}-{q}`` (when two
    lexfiles' groups picked the same qualifier for one base word), then its
    tier-1 slug. A candidate is kept only if no other concept in the whole build
    ends up with the same slug; the loop moves colliding candidates down one
    option at a time, so it stops after at most three passes and is deterministic.
    """
    counts = Counter(tier1.values())
    options: dict[str, list[str]] = {}
    for key, slug in tier1.items():
        qualifier = qualifiers.get(source_key_hash(key))
        if counts[slug] > 1 and qualifier:
            q = "-".join(w for w in slugify(qualifier).split("-") if w)
            options[key] = [f"{base_slugs[key]}-{q}", f"{slug}-{q}", slug]
    final = dict(tier1)
    choice = dict.fromkeys(options, 0)
    for key, tries in options.items():
        final[key] = tries[0]
    while True:
        counts = Counter(final.values())
        moved = False
        for key, tries in options.items():
            if counts[final[key]] > 1 and choice[key] < len(tries) - 1:
                choice[key] += 1
                final[key] = tries[choice[key]]
                moved = True
        if not moved:
            break
    applied = sum(1 for key in options if final[key] != tier1[key])
    lg.info("Applied {} tier-2 slug qualifier(s)", applied)
    return final, applied


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


def _relation_edges(
    grouped: Mapping[str, list[SynsetEntry]],
    key_to_cid: Mapping[tuple[str, str], str],
) -> tuple[set[tuple[str, str, str]], Counter[str], int]:
    """Resolve OMW synset relations to normalized ``(a, b, type)`` concept edges.

    Each target is a lexicon-local synset id in the same language, so it resolves
    through `key_to_cid` (built from every ingested synset). `SYNSET_RELATIONS`
    maps each ``wn`` name to its stored type and says whether to swap the
    endpoints, so ``x hyponym y`` and ``y hypernym x`` land on the same edge;
    symmetric types are put in canonical ``a < b`` order here, so the two halves
    of an unmirrored pair dedupe too. A target that does not resolve (filtered out
    / cross-lexicon) is counted as dangling and dropped, never emitted as a half
    edge; so is a link from a concept to itself.

    Contradictions: reading both names of a pair can surface a directional edge
    stated in *both* orientations. OMW 1.4 has one - the known WordNet 3.0
    ``restrain`` / ``inhibit`` cycle, where ``restrain`` lists ``inhibit`` as both
    its hypernym and its hyponym. Each orientation is scored by how many links
    state it; the better-supported one is kept (there, ``restrain -> inhibit``,
    stated twice against once), and a tie drops both rather than guess.

    Returns:
        The unique edges, the dropped-dangling counts per ``wn`` relation name,
        and the number of contradicted directional pairs that had to be resolved.
    """
    support, dangling = _relation_support(grouped, key_to_cid)
    edges: set[tuple[str, str, str]] = set()
    contradicted = 0
    for (a, b, rel), count in support.items():
        against = 0 if rel in SYMMETRIC_CONCEPT_RELATIONS else support[b, a, rel]
        if against and a < b:
            contradicted += 1  # count each contradicted pair once
        if count > against:
            edges.add((a, b, rel))
    return edges, dangling, contradicted


def _relation_support(
    grouped: Mapping[str, list[SynsetEntry]],
    key_to_cid: Mapping[tuple[str, str], str],
) -> tuple[Counter[tuple[str, str, str]], Counter[str]]:
    """Count how many source links state each normalized ``(a, b, type)`` edge.

    Returns:
        The per-edge support counts and the dangling counts per ``wn`` name.
    """
    support: Counter[tuple[str, str, str]] = Counter()
    dangling: Counter[str] = Counter()
    for group in grouped.values():
        for entry in group:
            source = key_to_cid.get((entry.language, entry.synset_id))
            if source is None:  # pragma: no cover - the entry is always in the map
                continue
            for name, targets in entry.relations.items():
                if name not in SYNSET_RELATIONS:
                    continue  # the reader already filters; guard fakes anyway
                stored, reverse = SYNSET_RELATIONS[name]
                for target in targets:
                    other = key_to_cid.get((entry.language, target))
                    if other is None:
                        dangling[name] += 1
                        continue
                    if other == source:  # OMW never self-links; guard anyway
                        continue
                    a, b = (other, source) if reverse else (source, other)
                    if stored in SYMMETRIC_CONCEPT_RELATIONS and a > b:
                        a, b = b, a
                    support[a, b, stored] += 1
    return support, dangling


def _sense_relation_edges(
    grouped: Mapping[str, list[SynsetEntry]],
    key_to_cid: Mapping[tuple[str, str], str],
    senses: Mapping[tuple[str, str], Sense],
) -> tuple[list[SenseRelation], set[tuple[str, str, str]], int]:
    """Resolve sense links to `SenseRelation` edges and derived concept edges.

    A link names a member form of its own synset and a form + synset on the
    target side; both resolve to a ``(lemma_id, concept_id)`` sense through the
    same `lemma_id` / `key_to_cid` keys the sense table was built on. Either end
    can fail to resolve - a target synset not ingested, or a form dropped as
    malformed - and is then counted and dropped, never half-emitted.

    Each resolved antonym also implies its two *concepts* are opposed; that
    concept-level ``antonym`` edge is derived here, since concepts are shared
    across languages and it is the only way the wordnets with no sense relations
    get opposites (phase 7 Decision 2).

    Returns:
        The sorted unique sense edges, the derived ``(a, b, type)`` concept edges
        (canonically ordered; antonymy is symmetric), and the dangling count.
    """
    sense_edges: set[tuple[str, str, str]] = set()
    derived: set[tuple[str, str, str]] = set()
    dangling = 0
    for group in grouped.values():
        for entry in group:
            source_cid = key_to_cid.get((entry.language, entry.synset_id))
            for link in entry.sense_links:
                target_cid = key_to_cid.get((entry.language, link.target_synset_id))
                if source_cid is None or target_cid is None:
                    dangling += 1
                    continue
                source_key = (
                    lemma_id(unescape_form(link.form), entry.language),
                    source_cid,
                )
                target_key = (
                    lemma_id(unescape_form(link.target_form), entry.language),
                    target_cid,
                )
                if source_key not in senses or target_key not in senses:
                    dangling += 1  # a form dropped as malformed, or not a member
                    continue
                low, high = sorted((senses[source_key].id, senses[target_key].id))
                if low == high:  # pragma: no cover - OMW never self-links
                    continue
                sense_edges.add((low, high, link.relation_type))
                if source_cid != target_cid:
                    a, b = sorted((source_cid, target_cid))
                    derived.add((a, b, link.relation_type))
    relations = [
        SenseRelation(sense_id_a=a, sense_id_b=b, relation_type=rel)
        for a, b, rel in sorted(sense_edges)
    ]
    return relations, derived, dangling


def _assemble_relations(
    grouped: Mapping[str, list[SynsetEntry]],
    key_to_cid: Mapping[tuple[str, str], str],
    senses: Mapping[tuple[str, str], Sense],
) -> tuple[list[ConceptRelation], list[str], list[SenseRelation]]:
    """Build both relation tables, tag each concept edge, and log what was dropped.

    A derived antonym edge that the source also states directly stays a read
    (`SOURCE_OMW`) edge; only edges the source does not state are `SOURCE_DERIVED`.

    Returns:
        The sorted concept edges, their provenance tags (parallel), and the sorted
        sense edges.
    """
    read_edges, dangling, contradicted = _relation_edges(grouped, key_to_cid)
    if dangling:
        lg.info("Dropped relation link(s) with no resolved target: {}", dict(dangling))
    if contradicted:
        lg.info("Resolved {} edge(s) stated in both directions", contradicted)
    sense_relations, derived_edges, sense_dangling = _sense_relation_edges(
        grouped,
        key_to_cid,
        senses,
    )
    if sense_dangling:
        lg.info("Dropped {} sense relation(s) with an unresolved end", sense_dangling)
    tagged = dict.fromkeys(read_edges, SOURCE_OMW)
    for edge in derived_edges:
        tagged.setdefault(edge, SOURCE_DERIVED)
    ordered = sorted(tagged)
    relations = [
        ConceptRelation(concept_id_a=a, concept_id_b=b, relation_type=rel)
        for a, b, rel in ordered
    ]
    return relations, [tagged[edge] for edge in ordered], sense_relations


def group_to_records(
    entries: Iterable[SynsetEntry],
    cili_glosses: Mapping[str, str] | None = None,
    slug_qualifiers: Mapping[str, str] | None = None,
) -> GroupedRecords:
    """Group flattened synset entries by ILI into concept/lemma/sense models.

    All entries that share an ILI become **one** `Concept` whose `definitions`
    map holds the per-language glosses; every member lemma of every language in
    the group becomes a thin `Lemma` and an attaching `Sense` edge. Lemmas are
    de-duplicated by `Lemma.id` (a form shared by two synsets is one token);
    senses are de-duplicated by ``(lemma_id, concept_id)``. Member forms pass
    through `unescape_form` first; those that then match `is_malformed_form`
    (wiki-anchor artifacts from phase 5.55 Q4, markup and placeholders from
    phase 5.57) are dropped with their would-be senses and counted in the log.

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
        slug_qualifiers: Accepted tier-2 slug qualifiers keyed by concept key
            (the curated ``slug_qualifiers.jsonl``); ``None`` stops at tier 1.

    Phase 5.5 Step 4 fields, all concept-level (ILI-keyed, so they propagate):
    each concept also gets its `lexfile` (from the English synset, see
    `_pick_lexfile`) and per-language `examples` (from the synset, see
    `_group_examples`).

    Relations (phase 7): the OMW synset links in `SYNSET_RELATIONS` become
    normalized `ConceptRelation` edges, both names of each inverse pair read and
    stored one way (see `_relation_edges`); English sense antonymy becomes
    `SenseRelation` edges plus derived concept-level ``antonym`` edges (see
    `_sense_relation_edges`). A link whose target does not resolve is dropped and
    logged, never emitted half-formed.

    SemCor counts (phase 6): `SynsetEntry.member_counts` rides along with the
    member forms, so the counts are attributed while the ILI group is still open -
    the only place they *can* be, since the corpus does not persist the ILI. Counts
    accumulate per sense and per concept; a form dropped as malformed drops its
    count with it, and a form that merges into an existing lemma adds to it.

    Returns:
        A `GroupedRecords` with the concepts, lemmas and senses (each sorted by id
        for determinism), the per-concept provenance tags parallel to the sorted
        concepts, the sorted unique `ConceptRelation` edges with their
        provenance tags, the sorted unique `SenseRelation` edges, and the SemCor
        sense/concept count maps.
    """
    glosses = cili_glosses or {}
    grouped: dict[str, list[SynsetEntry]] = {}
    for entry in entries:
        grouped.setdefault(_grouping_key(entry), []).append(entry)

    slugs, qualified = _tiered_slugs(grouped, slug_qualifiers)
    concepts: list[Concept] = []
    concept_source_by_id: dict[str, str] = {}
    lemmas: dict[str, Lemma] = {}
    senses: dict[tuple[str, str], Sense] = {}
    key_to_cid: dict[tuple[str, str], str] = {}
    sense_counts: dict[tuple[str, str], int] = {}
    concept_counts: dict[str, int] = {}
    concept_domains: dict[str, set[str]] = {}
    tally = _LemmaTally()
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
            if entry.domain_topics:
                concept_domains.setdefault(cid, set()).update(entry.domain_topics)
            pos = _POS_LABELS.get(entry.pos or "")
            # Registering the concept on *any* English entry (not just a tagged
            # one) is what lets phase 6 tell "English member, never tagged" (0)
            # from "no English member at all" (absent).
            is_count_language = entry.language == COUNT_LANGUAGE
            if is_count_language:
                concept_counts.setdefault(cid, 0)
            for raw_form, count in _forms_with_counts(entry):
                forms, dropped = member_forms(raw_form, entry.language)
                malformed_dropped += dropped
                for form in forms:
                    lemma = Lemma(
                        text=form,
                        language=entry.language,
                        part_of_speech=pos,
                        sources=["omw"],
                    )
                    lemmas.setdefault(lemma.id, lemma)
                    tally.add(lemma.id, form, pos)
                    senses.setdefault(
                        (lemma.id, cid),
                        Sense(lemma_id=lemma.id, concept_id=cid),
                    )
                    if is_count_language and count:
                        sense_counts[lemma.id, cid] = (
                            sense_counts.get((lemma.id, cid), 0) + count
                        )
                        concept_counts[cid] = concept_counts.get(cid, 0) + count

    relations, relation_sources, sense_relations = _assemble_relations(
        grouped,
        key_to_cid,
        senses,
    )
    if malformed_dropped:
        lg.info(
            "Dropped {} malformed member form(s) (5.55 Q4 / 5.57)",
            malformed_dropped,
        )

    concepts.sort(key=lambda c: c.id)
    settled = (tally.settle(lem) for lem in lemmas.values())
    sorted_lemmas = sorted(settled, key=lambda lem: lem.id)
    sorted_senses = sorted(senses.values(), key=lambda s: s.id)
    concept_sources = [concept_source_by_id[c.id] for c in concepts]
    return GroupedRecords(
        concepts=concepts,
        lemmas=sorted_lemmas,
        senses=sorted_senses,
        concept_sources=concept_sources,
        relations=relations,
        relation_sources=relation_sources,
        sense_relations=sense_relations,
        concept_domains=concept_domains,
        sense_counts=sense_counts,
        qualifiers_applied=qualified,
        concept_counts=concept_counts,
    )


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

    Each wordnet is opened with **no expansion** (``expand=""``). By default ``wn``
    lets a lexicon that has no relations of its own borrow another installed
    lexicon's, projected through the ILI - and in OMW 1.4 only English carries any
    relations. Read that way, the pt/es/fr/it "relations" were English's graph
    seen through each wordnet's partial coverage, which is why their hypernym and
    hyponym links looked unmirrored and why ~250k of them pointed at synsets the
    lexicon does not have. Concepts are grouped by ILI, so English's own edges
    already connect them; reading the projection again added nothing and
    misreported both the asymmetry and the dangling counts (phase 7).

    Args:
        langs: ISO 639-1 codes to read (e.g. ``["en", "pt"]``). Each maps to a
            single OMW lexicon via `OMW_LEXICONS`.
        data_dir: Optional override for ``wn``'s data directory; ``None`` uses
            its default (``~/.wn_data``).
        omw_version: OMW release version used to build the lexicon specifiers.

    Yields:
        One `SynsetEntry` per (synset, language).

    Raises:
        OptionalDependencyMissingError: When the ``ingest`` extra (``wn``) is not
            installed.
        UnknownOmwLanguageError: When a language has no mapped OMW lexicon.
    """
    wn = _require_wn()
    if data_dir is not None:
        wn.config.data_directory = data_dir  # pyright: ignore[reportPrivateImportUsage]
    for language in langs:
        spec = _omw_lexicon(language, omw_version)
        wordnet = wn.Wordnet(lexicon=spec, expand="")
        read_counts = language == COUNT_LANGUAGE
        for synset in wordnet.synsets():
            yield SynsetEntry(
                language=language,
                synset_id=synset.id,
                ili=_ili_id(synset),
                definition=synset.definition(),
                lemmas=tuple(synset.lemmas()),
                member_counts=_member_counts(synset) if read_counts else (),
                pos=synset.pos,
                lexfile=synset.lexfile(),
                examples=tuple(synset.examples()),
                relations=_synset_relations(synset),
                sense_links=_sense_links(synset),
                domain_topics=_domain_topics(synset),
            )


def _domain_topics(synset: Any) -> tuple[str, ...]:  # noqa: ANN401 - wn.Synset
    """Return the first member form of each ``domain_topic`` target, sorted."""
    targets = synset.relations().get("domain_topic", [])
    return tuple(sorted({t.lemmas()[0] for t in targets if t.lemmas()}))


def _synset_relations(synset: Any) -> dict[str, tuple[str, ...]]:  # noqa: ANN401 - wn.Synset
    """Return the synset's `SYNSET_RELATIONS` links as ``{name: target ids}``."""
    return {
        name: tuple(target.id for target in targets)
        for name, targets in synset.relations().items()
        if name in SYNSET_RELATIONS and targets
    }


def _sense_links(synset: Any) -> tuple[SenseLink, ...]:  # noqa: ANN401 - wn.Synset
    """Return the `SENSE_RELATIONS` links of the synset's member senses.

    Read for every language, not just English: only English carries any today,
    but nothing about the shape is English-specific, so a richer wordnet would be
    picked up without a code change.
    """
    return tuple(
        SenseLink(
            form=sense.word().lemma(),
            relation_type=name,
            target_synset_id=target.synset().id,
            target_form=target.word().lemma(),
        )
        for sense in synset.senses()
        for name, targets in sense.relations().items()
        if name in SENSE_RELATIONS
        for target in targets
    )


def _member_counts(synset: Any) -> tuple[int, ...]:  # noqa: ANN401 - wn.Synset
    """Return SemCor counts aligned to ``synset.lemmas()``, or ``()`` if none.

    ``wn`` exposes counts per *sense*, and ``Sense.counts()`` returns plain ints
    (verified against ``wn`` 0.9.5 - not count objects with a ``.value``). Senses
    come back in member order, but the alignment is rebuilt by lemma rather than
    assumed, so a source that ever reorders them cannot silently shift counts onto
    the wrong words.

    Args:
        synset: A ``wn`` synset.

    Returns:
        One total per member form, or an empty tuple when nothing is tagged (the
        common case: only English is tagged, and only 17% of its senses).
    """
    totals: dict[str, int] = {}
    for sense in synset.senses():
        counts = sense.counts()
        if counts:
            lemma = sense.word().lemma()
            totals[lemma] = totals.get(lemma, 0) + sum(counts)
    if not totals:
        return ()
    return tuple(totals.get(form, 0) for form in synset.lemmas())


def _require_wn():  # noqa: ANN202 - the wn module, kept lazy
    """Import ``wn`` lazily, mapping absence to a clear error."""
    try:
        import wn  # noqa: PLC0415 - lazy so the extra stays optional  # pyright: ignore[reportMissingImports]
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        package, extra = "wn", "ingest"
        raise OptionalDependencyMissingError(package, extra) from exc
    return wn
