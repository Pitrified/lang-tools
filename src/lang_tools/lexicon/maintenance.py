"""Propose -> review -> apply maintenance loop over the Parquet corpus.

Phase 05.55 built this as the first concrete run of the phase-8 maintenance
machinery: a deterministic **worklist** query finds defective rows, an LLM chain
(`lang_tools.llm.gloss_repair`) drafts a proposal per row, the proposals land in
a reviewable JSONL, and only human-accepted proposals are applied back to the
canonical Parquet. A thin notebook under ``notebooks/lexicon_maintain/`` drives
the loop; all the logic lives here.

The one worklist so far is the re-scoped ``definition == lemma`` residue: a
per-language gloss that equals the concept's *sole* member form in that language
(see `lang_tools.lexicon.quality`). Each worklist entry carries the context the
repair prompt is grounded in (member forms, the English gloss and members, the
lexfile, the hypernym's English gloss) so the chain cannot hallucinate meaning.

Provenance seam:
    The generic `corpus.export_table` / `import_table` round-trip does not carry
    the on-disk `source` column, so `apply_gloss_proposals` edits the concepts
    table directly at the raw-row level: it preserves every row's existing
    provenance tag and re-tags the rows it changes as ``llm``. Ids never change
    (glosses do not feed `concept_id`), so senses / relations stay valid.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from typing import Any
from typing import Literal
from typing import cast

from loguru import logger as lg
from pydantic import BaseModel
from pydantic import Field

from lang_tools.lexicon.codec import PROVENANCE_COL
from lang_tools.lexicon.codec import _dump_table
from lang_tools.lexicon.codec import _read_table_rows
from lang_tools.lexicon.codec import model_from_row
from lang_tools.lexicon.lemma_store import CorpusNotFoundError
from lang_tools.lexicon.quality import LEXICON_SUBDIR
from lang_tools.lexicon.quality import _connect
from lang_tools.lexicon.quality import _def_eq_sole_member_hits
from lang_tools.lexicon.quality import _table_sources

if TYPE_CHECKING:
    from pathlib import Path

    from lang_tools.lexicon.concept import Concept

#: Provenance tag applied to rows whose gloss an accepted proposal rewrote.
SOURCE_LLM = "llm"


class ProposalConceptNotFoundError(KeyError):
    """Raised when an accepted proposal targets a concept id not in the corpus."""

    def __init__(self, concept_id: str) -> None:
        """Initialize with the missing concept id.

        Args:
            concept_id: The proposal's target concept id.
        """
        super().__init__(f"No concept {concept_id!r} in the corpus.")
        self.concept_id = concept_id


class ThinGloss(BaseModel):
    """One `definition == lemma` worklist entry with its repair context.

    Attributes:
        concept_id: The affected concept.
        language: Language of the thin gloss.
        definition: The current gloss (equals `member`).
        member: The concept's sole member form in `language`.
        lexfile: The concept's WordNet lexicographer class, if any.
        english_definition: The concept's English gloss, if any.
        english_members: The concept's English member forms.
        hypernym_definition: English gloss of one hypernym concept, if any.
    """

    concept_id: str
    language: str
    definition: str
    member: str
    lexfile: str | None = None
    english_definition: str | None = None
    english_members: list[str] = Field(default_factory=list)
    hypernym_definition: str | None = None


class GlossProposal(BaseModel):
    """One reviewable gloss-repair proposal (a JSONL line).

    Attributes:
        concept_id: The affected concept.
        language: Language of the gloss to replace.
        current_definition: The gloss as it stands (the review anchor; apply
            refuses nothing on mismatch - ids are the key - but the reviewer
            sees what the proposal was made against).
        proposed_definition: The replacement gloss drafted by the chain.
        rationale: The chain's one-line grounding note (review aid only).
        status: ``proposed`` until a human flips it to ``accepted`` /
            ``rejected``; only accepted rows are applied.
    """

    concept_id: str
    language: str
    current_definition: str
    proposed_definition: str
    rationale: str = ""
    status: Literal["proposed", "accepted", "rejected"] = "proposed"


def thin_gloss_worklist(data_fol: Path) -> list[ThinGloss]:
    """Find the `definition == lemma` residue with its repair context.

    Runs the same sole-member hits query as the quality gate (shared CTE, so the
    worklist and the invariant can never drift), then enriches each hit with the
    concept-level context the repair prompt is grounded in.

    Args:
        data_fol: Project data folder; the corpus lives under
            ``<data_fol>/lexicon/``.

    Returns:
        One `ThinGloss` per offending (concept, language) pair, sorted by id.

    Raises:
        CorpusNotFoundError: When no Parquet corpus exists at the location.
        StoreDependencyMissingError: When the ``store`` extra (duckdb) is not
            installed.
    """
    corpus_dir = data_fol / LEXICON_SUBDIR
    if not (corpus_dir / "concepts.parquet").exists():
        raise CorpusNotFoundError(corpus_dir)
    t = _table_sources(data_fol)
    con = _connect()
    try:
        hits = con.execute(
            _def_eq_sole_member_hits(t)
            + "SELECT concept_id, lang, definition, lemma FROM hits "
            "ORDER BY concept_id, lang",
        ).fetchall()
        return [
            _enrich_hit(con, t, cid, lang, definition, member)
            for cid, lang, definition, member in hits
        ]
    finally:
        con.close()


def _enrich_hit(
    con: Any,  # noqa: ANN401 - duckdb connection, lazy optional dep
    t: dict[str, str],
    cid: str,
    lang: str,
    definition: str,
    member: str,
) -> ThinGloss:
    """Attach the concept-level prompt context to one worklist hit."""
    lexfile, en_def = con.execute(
        f"SELECT lexfile, definitions['en'] FROM {t['concepts']} "
        "WHERE id = ?",
        [cid],
    ).fetchone()
    en_members = [
        row[0]
        for row in con.execute(
            f"SELECT l.text FROM {t['senses']} s "
            f"JOIN {t['lemmas']} l ON l.id = s.lemma_id "
            "WHERE s.concept_id = ? AND l.language = 'en' ORDER BY l.text",
            [cid],
        ).fetchall()
    ]
    hyper = con.execute(
        f"SELECT c.definitions['en'] FROM {t['concept_relations']} r "
        f"JOIN {t['concepts']} c ON c.id = r.concept_id_b "
        "WHERE r.concept_id_a = ? AND r.relation_type = 'hypernym' "
        "AND c.definitions['en'] IS NOT NULL LIMIT 1",
        [cid],
    ).fetchone()
    return ThinGloss(
        concept_id=cid,
        language=lang,
        definition=definition,
        member=member,
        lexfile=lexfile,
        english_definition=en_def,
        english_members=en_members,
        hypernym_definition=hyper[0] if hyper else None,
    )


def write_proposals(proposals: list[GlossProposal], path: Path) -> Path:
    """Write proposals to a reviewable JSONL file (one proposal per line).

    Args:
        proposals: The proposals to persist.
        path: Destination JSONL path (staging scratch; never committed).

    Returns:
        The path written.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for proposal in proposals:
            fh.write(json.dumps(proposal.model_dump(), ensure_ascii=False))
            fh.write("\n")
    return path


def read_proposals(path: Path) -> list[GlossProposal]:
    """Read a (reviewed) proposals JSONL back into validated models.

    Args:
        path: The JSONL written by `write_proposals`, possibly hand-edited
            (typically: `status` flipped and/or `proposed_definition` refined).

    Returns:
        The validated proposals.
    """
    with path.open("r", encoding="utf-8") as fh:
        return [
            GlossProposal.model_validate(json.loads(line))
            for line in fh
            if line.strip()
        ]


def apply_gloss_proposals(
    proposals: list[GlossProposal],
    *,
    data_fol: Path,
) -> int:
    """Apply the **accepted** proposals to the concepts Parquet, re-tagging `llm`.

    Edits at the raw-row level so every untouched row keeps its existing
    provenance tag; each edited row's tag becomes ``llm``. Rows still validate
    through the `Concept` model before the table is rewritten. Concept ids do
    not change, so no other table is touched.

    Args:
        proposals: Reviewed proposals; only ``status == "accepted"`` rows apply.
        data_fol: Project data folder.

    Returns:
        The number of concepts rewritten (0 skips the table rewrite entirely).

    Raises:
        ProposalConceptNotFoundError: When an accepted proposal's concept id is
            not in the corpus.
    """
    accepted = {
        (p.concept_id, p.language): p for p in proposals if p.status == "accepted"
    }
    if not accepted:
        return 0

    rows = _read_table_rows("concepts", data_fol=data_fol)
    rows_by_id = {row["id"]: row for row in rows}
    for cid, _lang in accepted:
        if cid not in rows_by_id:
            raise ProposalConceptNotFoundError(cid)

    has_provenance = bool(rows) and PROVENANCE_COL in rows[0]
    models: list[Concept] = []
    sources: list[str] = []
    applied = set()
    for row in rows:
        model = cast("Concept", model_from_row("concepts", row))
        # A null tag stays empty rather than inventing a source.
        tag = row.get(PROVENANCE_COL) or ""
        for (cid, lang), proposal in accepted.items():
            if cid == row["id"]:
                model.definitions[lang] = proposal.proposed_definition
                tag = SOURCE_LLM
                applied.add(cid)
        models.append(model)
        sources.append(tag)

    _dump_table(
        "concepts",
        models,
        data_fol=data_fol,
        sources=sources if has_provenance else None,
    )
    lg.info("Applied {} accepted gloss proposal(s)", len(applied))
    return len(applied)
