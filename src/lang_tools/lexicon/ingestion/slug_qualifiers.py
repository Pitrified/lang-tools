"""Slug tier 2: gloss-derived qualifiers for still-colliding concept slugs (phase 8).

5.55 shipped slug tiers 0-1 (the preferred lemma, then the lexfile when it
collides) and specified tier 2 for what is left: an LLM qualifier taken from the
English gloss, reviewed, then a **committed build input**. This module is both
ends of that:

- the **worklist**: `collision_groups` reads the corpus for every slug more than
  one concept shares, with each concept's English gloss and members;
- the **acceptance check**: `check_qualifiers` turns one chain output into
  `SlugQualifier` rows, accepting a qualifier only when it is 1-3 words, every
  word comes from that concept's own gloss, it is not just the base word, and no
  other concept in the group got the same one. This is the mechanical rule the
  phase-8 decision allows to auto-accept: a qualifier built only from gloss words
  cannot put a meaning into an id that the gloss does not already state;
- the **build input**: `load_slug_qualifiers` reads the accepted rows of
  ``data/curated/slug_qualifiers.jsonl``, keyed by `concept_key` so they survive
  the very re-slug they cause; `sources.omw._tiered_slugs` applies them.

A rejected or missing qualifier is not an error: that concept keeps its tier-1
slug, and the hash keeps every id unique regardless.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
from typing import TYPE_CHECKING

from pydantic import BaseModel

from lang_tools.language.normalization import normalize
from lang_tools.lexicon.codec import LEXICON_SUBDIR
from lang_tools.lexicon.concept_id import concept_key
from lang_tools.lexicon.ingestion.sources.omw import slugify
from lang_tools.lexicon.lemma_store import CorpusNotFoundError
from lang_tools.lexicon.maintenance import ReviewStatus
from lang_tools.lexicon.maintenance import load_curated
from lang_tools.lexicon.quality import _connect
from lang_tools.lexicon.quality import _table_sources
from lang_tools.llm.slug_qualifier import QualifierCandidate
from lang_tools.llm.slug_qualifier import SlugQualifierInput

if TYPE_CHECKING:
    from pathlib import Path

    from lang_tools.llm.slug_qualifier import SlugQualifierOutput

#: Committed curated qualifier table, under ``<data_fol>/curated/``.
SLUG_QUALIFIERS_FILE = "slug_qualifiers.jsonl"

#: Longest qualifier accepted, in slug words.
MAX_QUALIFIER_WORDS = 3

#: English member forms shown per concept (context only; never qualifier words).
_MEMBERS_SHOWN = 6


class SlugQualifier(BaseModel):
    """One concept's qualifier decision (a curated JSONL line).

    Attributes:
        concept_key: The concept's slug-independent key (`concept_key`).
        slug: The slug the concept shared when the qualifier was proposed.
        qualifier: The proposed qualifier, as the chain returned it.
        status: ``accepted`` when it passed `check_qualifiers`, else ``rejected``.
        reason: Why it was rejected (empty when accepted).
        model: The model that proposed it.
        prompt_sha: Hash of the prompt template that produced it.
    """

    concept_key: str
    slug: str
    qualifier: str
    status: ReviewStatus
    reason: str = ""
    model: str = ""
    prompt_sha: str = ""


@dataclass(frozen=True)
class CollisionGroup:
    """Every concept that shares one slug.

    Attributes:
        slug: The shared slug (tier 1).
        base: The tier-0 base word(s) the slug was built from.
        concepts: The group's concepts as the prompt shows them.
    """

    slug: str
    base: str
    concepts: list[QualifierCandidate]

    def chain_input(self) -> SlugQualifierInput:
        """Return the chain input for this group."""
        return SlugQualifierInput(
            slug=self.slug,
            base=self.base,
            concepts=self.concepts,
        )


def base_of(slug: str, lexfile: str | None) -> str:
    """Return the tier-0 base of a slug by dropping its tier-1 lexfile suffix."""
    suffix = f"-{slugify(lexfile)}" if lexfile else ""
    if suffix and slug.endswith(suffix) and len(slug) > len(suffix):
        return slug[: -len(suffix)]
    return slug


def collision_groups(data_fol: Path) -> list[CollisionGroup]:
    """Read every slug shared by more than one concept, with gloss context.

    Args:
        data_fol: Project data folder; the corpus lives under ``<data_fol>/lexicon/``.

    Returns:
        The collision groups, sorted by slug; each group's concepts by key.

    Raises:
        CorpusNotFoundError: When no Parquet corpus exists at the location.
    """
    corpus_dir = data_fol / LEXICON_SUBDIR
    if not (corpus_dir / "concepts.parquet").exists():
        raise CorpusNotFoundError(corpus_dir)
    t = _table_sources(data_fol)
    con = _connect()
    try:
        rows = con.execute(
            f"""
WITH s AS (
  SELECT id, regexp_extract(id, '^c__(.*)__[0-9a-f]+$', 1) AS slug,
         definitions['en'] AS gloss, lexfile
  FROM {t["concepts"]}
),
shared AS (SELECT slug FROM s GROUP BY slug HAVING count(*) > 1),
members AS (
  SELECT x.concept_id, list(l.text ORDER BY l.text) AS forms
  FROM {t["senses"]} x JOIN {t["lemmas"]} l ON l.id = x.lemma_id
  WHERE l.language = 'en' GROUP BY x.concept_id
)
SELECT s.slug, s.id, coalesce(s.gloss, ''), s.lexfile, coalesce(m.forms, [])
FROM s JOIN shared USING (slug) LEFT JOIN members m ON m.concept_id = s.id
ORDER BY s.slug, s.id
""",
        ).fetchall()
    finally:
        con.close()
    groups: dict[str, list[tuple[str, str, str | None, list[str]]]] = {}
    for slug, cid, gloss, lexfile, forms in rows:
        groups.setdefault(slug, []).append((cid, gloss, lexfile, forms))
    out = []
    for slug, members in groups.items():
        candidates = sorted(
            (
                QualifierCandidate(
                    key=concept_key(cid),
                    gloss=gloss,
                    members=", ".join(forms[:_MEMBERS_SHOWN]),
                )
                for cid, gloss, _lexfile, forms in members
            ),
            key=lambda c: c.key,
        )
        out.append(
            CollisionGroup(
                slug=slug,
                base=base_of(slug, members[0][2]),
                concepts=candidates,
            ),
        )
    return out


def check_qualifiers(
    group: CollisionGroup,
    output: SlugQualifierOutput,
    *,
    model: str = "",
    prompt_sha: str = "",
) -> list[SlugQualifier]:
    """Accept or reject each concept's proposed qualifier (pure).

    Args:
        group: The collision group the chain saw.
        output: The chain's output for it.
        model: The model that produced `output` (recorded on each row).
        prompt_sha: The prompt hash (recorded on each row).

    Returns:
        One row per concept in the group, in the group's order.
    """
    proposed = {q.key: q.qualifier for q in output.qualifiers}
    slugs = {key: "-".join(slug_words(text)) for key, text in proposed.items()}
    slugs = {key: slug for key, slug in slugs.items() if slug}
    taken = Counter(slugs.values())
    rows = []
    for concept in group.concepts:
        qualifier = proposed.get(concept.key, "")
        reason = _rejection(concept, qualifier, group.base, slugs, taken)
        rows.append(
            SlugQualifier(
                concept_key=concept.key,
                slug=group.slug,
                qualifier=qualifier,
                status="rejected" if reason else "accepted",
                reason=reason,
                model=model,
                prompt_sha=prompt_sha,
            ),
        )
    return rows


def _rejection(
    concept: QualifierCandidate,
    qualifier: str,
    base: str,
    slugs: dict[str, str],
    taken: Counter[str],
) -> str:
    """Return why `qualifier` is not acceptable for `concept`, or ``""``."""
    if not qualifier.strip() or concept.key not in slugs:
        return "missing"
    slug = slugs[concept.key]
    words = slug.split("-")
    if not 1 <= len(words) <= MAX_QUALIFIER_WORDS:
        return "length"
    if slug == base:
        return "repeats the base word"
    gloss_words = set(slug_words(concept.gloss))
    if any(word not in gloss_words for word in words):
        return "word not in gloss"
    if taken[slug] > 1:
        return "duplicate within group"
    return ""


def slug_words(text: str) -> list[str]:
    """Return every slug word of `text`: `slugify`'s normalization, no word cap."""
    cleaned = re.sub(r"[^a-z0-9]+", "-", normalize(text)).strip("-")
    return cleaned.split("-") if cleaned else []


def load_slug_qualifiers(data_fol: Path) -> dict[str, str]:
    """Return the accepted qualifiers, ``{concept_key: qualifier}``, if any."""
    return {
        row.concept_key: row.qualifier
        for row in load_curated(SlugQualifier, data_fol, SLUG_QUALIFIERS_FILE)
    }
