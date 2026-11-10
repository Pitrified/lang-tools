"""Reviewed concept additions: create a concept the sources lack.

Every concept comes from a WordNet synset, and WordNet models nouns, verbs,
adjectives and adverbs only: the modal verbs have no concept, so pt *pode*
"can" or *deve* "must" can be linked to nothing (en *can* is a tin can, *must*
is grape juice). A concept addition is the reviewed fix:

- `ConceptAddition` is one row, keyed on a manual ``source_key``
  (``manual:can-be-able``), which feeds the id's hash exactly as a synset key
  does, so its `concept_key` is stable across rebuilds and re-slugs;
- the committed ``data/curated/concept_additions.jsonl`` holds the rows, and
  only the latest row of a key counts, so a later ``add: false`` row retracts
  one;
- `apply_concept_additions` runs as a build stage right before the sense
  additions, so a `sense_additions.SenseAddition` can link a lemma of any
  language to the new concept. It creates the concept with its English gloss,
  and links its English members, creating the lemmas the build lacks.

The concept and its edges are tagged ``manual``. A row whose key is already a
source concept's, or whose slug is not a valid id slug, is counted as stale and
skipped, never fatal (the curated-input rule).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger as lg
from pydantic import BaseModel

from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.concept_id import CONCEPT_ID_RE
from lang_tools.lexicon.concept_id import concept_id
from lang_tools.lexicon.concept_id import concept_key
from lang_tools.lexicon.concept_id import source_key_hash
from lang_tools.lexicon.ingestion.transform import SOURCE_MANUAL
from lang_tools.lexicon.lemma import Lemma
from lang_tools.lexicon.maintenance import ReviewStatus
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import read_jsonl
from lang_tools.lexicon.sense import Sense

if TYPE_CHECKING:
    from pathlib import Path

    from lang_tools.lexicon.ingestion.transform import TaggedTables

#: Committed curated concept additions, under ``<data_fol>/curated/``.
CONCEPT_ADDITIONS_FILE = "concept_additions.jsonl"

#: Lexfile class -> the lemma part-of-speech label, for a lemma a row creates.
_LEXFILE_POS = {"noun": "noun", "verb": "verb", "adj": "adjective", "adv": "adverb"}


class ConceptAddition(BaseModel):
    """One reviewed concept the sources lack (a JSONL line).

    Attributes:
        source_key: Stable key of the concept, ``manual:<name>``; hashed into
            the id like a synset key, so `concept_key` reads back its hash.
        slug: Human-readable slug of the id (lowercase, digits, hyphens).
        lexfile: The nearest WordNet lexicographer class (``verb.stative``);
            it gives a created lemma its part of speech.
        definition: The English gloss.
        members: The English words that realise the concept.
        add: True to add the concept; a later False row retracts it.
        reason: Why the concept is needed.
        status: ``proposed`` until accepted; only ``accepted`` rows apply.
        model: The reviewer (an agent tag, or ``manual``).
        prompt_sha: Hash of the rulebook the reviewer followed.
        batch: The review batch that wrote the row.
    """

    source_key: str
    slug: str
    lexfile: str
    definition: str
    members: list[str]
    add: bool = True
    reason: str = ""
    status: ReviewStatus = "proposed"
    model: str = ""
    prompt_sha: str = ""
    batch: str = ""

    @property
    def key(self) -> str:
        """The row key, its ``source_key``."""
        return self.source_key

    @property
    def concept_key(self) -> str:
        """The `concept_key` of the concept the row creates."""
        return source_key_hash(self.source_key)


def load_concept_additions(data_fol: Path) -> list[ConceptAddition]:
    """Return the latest row per key of the committed file, if accepted.

    Only the newest row of a ``source_key`` counts, so a later ``add: false``
    row retracts an earlier addition.
    """
    path = curated_path(data_fol, CONCEPT_ADDITIONS_FILE)
    if not path.exists():
        return []
    latest: dict[str, ConceptAddition] = {}
    for row in read_jsonl(ConceptAddition, path):
        latest.pop(row.key, None)
        latest[row.key] = row
    return [row for row in latest.values() if row.status == "accepted"]


def apply_concept_additions(
    tables: TaggedTables, rows: list[ConceptAddition]
) -> tuple[int, int, int]:
    """Add the accepted concepts, their English members and lemmas, in place.

    Args:
        tables: The transformed tables, after the member-form drops.
        rows: Accepted rows, typically from `load_concept_additions`.

    Returns:
        ``(concepts added, lemmas created, stale)``.
    """
    keys = {concept_key(c.id) for c in tables.concepts}
    lemmas = {lemma.id for lemma in tables.lemmas}
    added = created = stale = 0
    for row in rows:
        if not row.add:
            continue
        cid = concept_id(row.slug, row.source_key)
        if row.concept_key in keys or not CONCEPT_ID_RE.match(cid):
            stale += 1
            continue
        tables.concepts.append(
            Concept(id=cid, definitions={"en": row.definition}, lexfile=row.lexfile)
        )
        tables.concept_sources.append(SOURCE_MANUAL)
        keys.add(row.concept_key)
        added += 1
        pos = _LEXFILE_POS.get(row.lexfile.split(".")[0])
        for word in row.members:
            lemma = Lemma(
                text=word, language="en", part_of_speech=pos, sources=[SOURCE_MANUAL]
            )
            if lemma.id not in lemmas:
                tables.lemmas.append(lemma)
                tables.lemma_sources.append(SOURCE_MANUAL)
                lemmas.add(lemma.id)
                created += 1
            tables.senses.append(Sense(lemma_id=lemma.id, concept_id=cid))
            tables.sense_sources.append(SOURCE_MANUAL)
    lg.info(
        "Concept additions: {} concept(s) added, {} lemma(s) created, {} stale",
        added,
        created,
        stale,
    )
    return added, created, stale
