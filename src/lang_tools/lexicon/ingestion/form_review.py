"""Member-form review: drop the "words" that are not words (phase 8).

5.57 removed the deterministic junk (MultiWordNet gap markers, markup). What it
left for review is fuzzier: 931 non-English member forms of five words or more,
or over 40 characters. Most are legitimate - proper names ("Académie militaire de
West Point"), multiword terms ("transistor à effet de champ") - but some are a
definition pasted in as a word (pt "artéria que irriga o coração"), text in the
wrong language (pt "track to track seek time"), or a garbled duplicate.

That is a judgement call per form, so this is the propose-for-review loop, not a
rule:

- `suspicious_forms` is the worklist, one item per (lemma, concept) sense, with
  the concept's English gloss and members as context;
- `FormDrop` is the reviewable row a `form_review` chain verdict becomes, written
  ``proposed``; a human flips a row to ``accepted``;
- the accepted rows of the committed ``data/curated/member_form_drops.jsonl`` are
  applied by `apply_form_drops` as a build stage, so a drop survives a rebuild
  like every other curated input. Rows key on ``lemma_id`` and `concept_key`,
  both of which are stable across rebuilds and re-slugs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger as lg
from pydantic import BaseModel

from lang_tools.lexicon.codec import LEXICON_SUBDIR
from lang_tools.lexicon.concept_id import concept_key
from lang_tools.lexicon.lemma_store import CorpusNotFoundError
from lang_tools.lexicon.maintenance import ReviewStatus
from lang_tools.lexicon.maintenance import load_curated
from lang_tools.lexicon.quality import _connect
from lang_tools.lexicon.quality import _table_sources
from lang_tools.llm.form_review import FormReviewInput

if TYPE_CHECKING:
    from pathlib import Path

    from lang_tools.lexicon.ingestion.transform import TaggedTables

#: Committed curated drop list, under ``<data_fol>/curated/``.
MEMBER_FORM_DROPS_FILE = "member_form_drops.jsonl"

#: A non-English form is suspicious when it has this many words or more...
MIN_SUSPICIOUS_WORDS = 5
#: ...or more characters than this.
MAX_PLAIN_LENGTH = 40


class FormDrop(BaseModel):
    """One reviewed member-form verdict (a JSONL line).

    Attributes:
        lemma_id: The lemma whose sense is reviewed.
        concept_key: The concept the sense points at (`concept_key`).
        language: The form's language.
        form: The form as it appears in the corpus (review aid).
        kind: The chain's classification (``term``, ``definition``, ...).
        drop: The chain's verdict.
        reason: The chain's one-line reason.
        status: ``proposed`` until a human accepts or rejects the drop.
        model: The model that produced the verdict.
        prompt_sha: Hash of the prompt template that produced it.
    """

    lemma_id: str
    concept_key: str
    language: str
    form: str
    kind: str
    drop: bool
    reason: str = ""
    status: ReviewStatus = "proposed"
    model: str = ""
    prompt_sha: str = ""

    @property
    def key(self) -> str:
        """The worklist key, ``{lemma_id}:{concept_key}``."""
        return f"{self.lemma_id}:{self.concept_key}"


def suspicious_forms(data_fol: Path) -> list[tuple[str, FormReviewInput]]:
    """Return the review worklist: ``(key, chain input)`` per suspicious sense.

    Args:
        data_fol: Project data folder; the corpus lives under ``<data_fol>/lexicon/``.

    Returns:
        Items sorted by key, the key being ``{lemma_id}:{concept_key}``.

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
WITH members AS (
  SELECT s.concept_id, l.language, l.id AS lemma_id, l.text
  FROM {t["senses"]} s JOIN {t["lemmas"]} l ON l.id = s.lemma_id
)
SELECT m.lemma_id, m.concept_id, m.language, m.text,
       coalesce(c.definitions['en'], ''),
       (SELECT list(e.text ORDER BY e.text) FROM members e
         WHERE e.concept_id = m.concept_id AND e.language = 'en'),
       (SELECT list(o.text ORDER BY o.text) FROM members o
         WHERE o.concept_id = m.concept_id AND o.language = m.language
           AND o.lemma_id <> m.lemma_id)
FROM members m JOIN {t["concepts"]} c ON c.id = m.concept_id
WHERE m.language <> 'en'
  AND (len(string_split(m.text, ' ')) >= {MIN_SUSPICIOUS_WORDS}
       OR length(m.text) > {MAX_PLAIN_LENGTH})
""",
        ).fetchall()
    finally:
        con.close()
    items = [
        (
            f"{lemma}:{concept_key(cid)}",
            FormReviewInput(
                language=language,
                form=text,
                english_definition=gloss,
                english_members=list(en_members or []),
                other_forms=list(others or []),
            ),
        )
        for lemma, cid, language, text, gloss, en_members, others in rows
    ]
    return sorted(items, key=lambda item: item[0])


def apply_form_drops(tables: TaggedTables, drops: list[FormDrop]) -> tuple[int, int]:
    """Remove accepted dropped senses, and lemmas left without one, in place.

    Called by `ingestion.pipeline.build_initial` right after `transform`, so the
    enrichment, the topics and the sample never see the dropped senses. A row that
    names a sense the build does not have is skipped (its form may already have
    been fixed upstream); it is not an error.

    Args:
        tables: The freshly transformed tables, mutated in place.
        drops: Accepted drops, typically from `load_form_drops`.

    Returns:
        ``(senses dropped, lemmas removed)``.
    """
    targets = {(d.lemma_id, d.concept_key) for d in drops if d.drop}
    if not targets:
        return (0, 0)
    kept_senses, kept_tags, dropped_ids = [], [], set()
    for sense, tag in zip(tables.senses, tables.sense_sources, strict=True):
        if (sense.lemma_id, concept_key(sense.concept_id)) in targets:
            dropped_ids.add(sense.id)
            tables.sense_counts.pop((sense.lemma_id, sense.concept_id), None)
            continue
        kept_senses.append(sense)
        kept_tags.append(tag)
    tables.senses, tables.sense_sources = kept_senses, kept_tags
    if tables.sense_relations:
        pairs = [
            (rel, tag)
            for rel, tag in zip(
                tables.sense_relations,
                tables.sense_relation_sources,
                strict=True,
            )
            if rel.sense_id_a not in dropped_ids and rel.sense_id_b not in dropped_ids
        ]
        tables.sense_relations = [rel for rel, _ in pairs]
        tables.sense_relation_sources = [tag for _, tag in pairs]
    with_sense = {sense.lemma_id for sense in kept_senses}
    pairs_l = [
        (lemma, tag)
        for lemma, tag in zip(tables.lemmas, tables.lemma_sources, strict=True)
        if lemma.id in with_sense
    ]
    removed = len(tables.lemmas) - len(pairs_l)
    tables.lemmas = [lemma for lemma, _ in pairs_l]
    tables.lemma_sources = [tag for _, tag in pairs_l]
    lg.info(
        "Dropped {} reviewed member-form sense(s), {} lemma(s)",
        len(dropped_ids),
        removed,
    )
    return (len(dropped_ids), removed)


def load_form_drops(data_fol: Path) -> list[FormDrop]:
    """Return the accepted rows of the committed member-form drop list."""
    return load_curated(FormDrop, data_fol, MEMBER_FORM_DROPS_FILE)
