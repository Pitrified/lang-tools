"""Agent-written pt glosses: served batches of the backfill worklist.

The same worklist as the OpenAI backfill (`gloss_backfill.missing_glosses`),
written by agent-harness subagents instead of the paid chain, over the batch
plumbing of the reviews (`review_batches`):

- `serve_batch` reserves the next ``size`` missing pt glosses as a batch file
  under ``data/work/gloss_write/``, skipping keys already pending or written;
- the writer answers one ``n gloss`` line per item, following the rules of the
  ``gloss_translate`` prompt the backfill uses;
- `apply_batch` screens every gloss with `gloss_backfill.check_glosses` and
  refuses the whole batch while any fails, so no rejected row is ever written;
  a clean batch appends ``proposed`` rows to ``data/curated/gloss_backfill.jsonl``
  and one row to the batch log, which records the rules hash and the keys.

The rows are accepted by sampled review (`gloss_backfill.accept_run`), as the
OpenAI run was. The build applies the first accepted backfill row of a concept,
so a wrong gloss is corrected with `correct_gloss`, an accepted row in the
gloss overrides, which the build applies first and which always win.
"""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
import re
from typing import TYPE_CHECKING

from loguru import logger as lg
from pydantic import BaseModel
from pydantic import Field

from lang_tools.lexicon.concept_id import concept_key
from lang_tools.lexicon.ingestion.gloss_backfill import BackfillItem
from lang_tools.lexicon.ingestion.gloss_backfill import check_glosses
from lang_tools.lexicon.ingestion.gloss_backfill import missing_glosses
from lang_tools.lexicon.ingestion.review_batches import LabelError
from lang_tools.lexicon.ingestion.review_batches import append_rows
from lang_tools.lexicon.ingestion.review_batches import guide_sha
from lang_tools.lexicon.ingestion.review_batches import locked
from lang_tools.lexicon.ingestion.review_batches import work_dir
from lang_tools.lexicon.maintenance import GLOSS_BACKFILL_FILE
from lang_tools.lexicon.maintenance import GlossProposal
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import gloss_overrides_path
from lang_tools.lexicon.maintenance import read_jsonl
from lang_tools.llm.gloss_translate import GlossTranslateOutput
from lang_tools.llm.gloss_translate import KeyedGloss

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

#: The language the agent batches write.
LANGUAGE = "pt"
#: One row per applied batch, under ``data/curated/``.
LOG_FILE = "gloss_write_log.jsonl"
#: Served, not yet applied batches live here, under the data folder (not committed).
WORK_SUBDIR = "work/gloss_write"
#: Items per batch, as the review batches.
DEFAULT_BATCH_SIZE = 200
#: The writer tag on the log rows.
WRITER = "agent-write"
#: The rules every gloss is written against, relative to the repo root.
RULES = "src/lang_tools/prompts/gloss_translate/v3.jinja"

_LINE_RE = re.compile(r"^(\d+)\s+(.*\S)\s*$")


class GlossCorrectionError(KeyError):
    """A correction names a key with no written pt gloss to correct."""


class GlossWriteItem(BaseModel):
    """One served gloss to write (a line of a batch file).

    Attributes:
        n: The item number the writer answers with.
        concept_id: The concept to gloss.
        english_definition: The English gloss to render.
        english_members: The concept's English words.
        target_members: The concept's pt words.
    """

    n: int
    concept_id: str
    english_definition: str
    english_members: list[str]
    target_members: list[str]

    @property
    def key(self) -> str:
        """The backfill key, ``pt:{concept_key}``."""
        return f"{LANGUAGE}:{concept_key(self.concept_id)}"

    def backfill_item(self) -> BackfillItem:
        """Return the item as the backfill screen reads it."""
        return BackfillItem(
            concept_id=self.concept_id,
            language=LANGUAGE,
            english_definition=self.english_definition,
            english_members=tuple(self.english_members),
            target_members=tuple(self.target_members),
        )


class GlossWriteLogRow(BaseModel):
    """One applied batch (a line of the batch log).

    Attributes:
        batch: The batch id.
        language: The language written.
        rules_sha: Hash of the rules file the batch was written against.
        writer: Who wrote the glosses.
        applied_at: When the batch was applied (UTC, ISO 8601).
        items: Glosses written.
        keys: The backfill keys written, so a key is never served twice.
    """

    batch: str
    language: str = LANGUAGE
    rules_sha: str = ""
    writer: str = WRITER
    applied_at: str = ""
    items: int = 0
    keys: list[str] = Field(default_factory=list)


class GlossWriteStatus(BaseModel):
    """Progress of the agent batches.

    Attributes:
        left: Missing pt glosses neither pending nor written.
        pending: Served batch ids not yet applied.
        batches: Applied batches.
        written: Glosses written by the applied batches.
    """

    left: int
    pending: list[str]
    batches: int
    written: int


def _log_rows(data_fol: Path) -> list[GlossWriteLogRow]:
    path = curated_path(data_fol, LOG_FILE)
    return read_jsonl(GlossWriteLogRow, path) if path.exists() else []


def _pending(data_fol: Path) -> dict[str, list[GlossWriteItem]]:
    return {
        path.stem: read_jsonl(GlossWriteItem, path)
        for path in sorted(work_dir(data_fol, WORK_SUBDIR).glob("*.jsonl"))
    }


def _todo(
    data_fol: Path,
    pending: dict[str, list[GlossWriteItem]],
    logs: Sequence[GlossWriteLogRow],
) -> list[BackfillItem]:
    """Return the missing pt glosses not pending and not written, by key.

    Written rows reach the corpus only at the next rebuild, so the log, not the
    corpus, is what keeps a written key from being served again.
    """
    taken = {item.key for items in pending.values() for item in items}
    taken |= {key for row in logs for key in row.keys}
    return [
        item
        for item in missing_glosses(data_fol, languages=[LANGUAGE])
        if item.key not in taken
    ]


def serve_batch(
    data_fol: Path,
    *,
    batch: str,
    size: int = DEFAULT_BATCH_SIZE,
) -> list[GlossWriteItem]:
    """Reserve the next missing pt glosses as a batch.

    The worklist is key-sorted, and the key is a hash, so a batch is an
    effectively random draw. Serving an id that is already pending returns that
    batch unchanged.

    Args:
        data_fol: Project data folder (the corpus is read from it).
        batch: The batch id (e.g. ``g0001``).
        size: Glosses to reserve.

    Returns:
        The batch items (empty when nothing is left to serve).

    Raises:
        ValueError: When the batch id was already applied.
    """
    with locked(data_fol, WORK_SUBDIR):
        pending = _pending(data_fol)
        if batch in pending:
            return pending[batch]
        logs = _log_rows(data_fol)
        if any(row.batch == batch for row in logs):
            msg = f"batch {batch} was already applied"
            raise ValueError(msg)
        picked = _todo(data_fol, pending, logs)[:size]
        items = [
            GlossWriteItem(
                n=n,
                concept_id=item.concept_id,
                english_definition=item.english_definition,
                english_members=list(item.english_members),
                target_members=list(item.target_members),
            )
            for n, item in enumerate(picked, start=1)
        ]
        if items:
            append_rows(work_dir(data_fol, WORK_SUBDIR) / f"{batch}.jsonl", items)
            lg.info("Served batch {}: {} gloss(es)", batch, len(items))
        return items


def render_batch(items: Sequence[GlossWriteItem]) -> str:
    """Return the batch as the lines a writer reads."""
    return "\n".join(
        f"{item.n} | {item.english_definition} | {', '.join(item.english_members)}"
        f" | {', '.join(item.target_members)}"
        for item in items
    )


def parse_glosses(
    batch: str,
    text: str,
    items: Sequence[GlossWriteItem],
) -> dict[int, str]:
    """Parse a writer's ``n gloss`` lines and screen every gloss.

    Args:
        batch: The batch id (for the error).
        text: The writer's lines; blank lines are ignored.
        items: The served items.

    Returns:
        The gloss of each item number.

    Raises:
        LabelError: Listing every problem: an unreadable line, an unknown,
            doubled or missing number, or a gloss the backfill screen rejects.
    """
    by_n = {item.n: item for item in items}
    glosses: dict[int, str] = {}
    problems: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        match = _LINE_RE.match(line.strip())
        if match is None:
            problems.append(f"unreadable line: {line.strip()!r}")
            continue
        n, gloss = int(match.group(1)), match.group(2)
        if n not in by_n:
            problems.append(f"{n}: no such item")
        elif n in glosses:
            problems.append(f"{n}: written twice")
        else:
            glosses[n] = gloss
    problems += [f"{n}: missing" for n in sorted(set(by_n) - set(glosses))]
    for n, gloss in sorted(glosses.items()):
        item = by_n[n]
        output = GlossTranslateOutput(
            glosses=[KeyedGloss(key=item.key, definition=gloss)],
        )
        (row,) = check_glosses([item.backfill_item()], output)
        if row.status == "rejected":
            problems.append(f"{n}: {row.rationale} ({gloss!r})")
    if problems:
        raise LabelError(batch, problems)
    return glosses


def apply_batch(
    data_fol: Path,
    batch: str,
    text: str,
    *,
    rules_path: Path,
) -> GlossWriteLogRow:
    """Screen a batch's glosses and append them as proposed backfill rows.

    Nothing is written while any gloss fails: the writer fixes the listed
    problems and applies again.

    Args:
        data_fol: Project data folder.
        batch: The served batch id.
        text: The writer's ``n gloss`` lines.
        rules_path: The rules file, hashed into the log row.

    Returns:
        The batch's log row (also appended to the batch log).

    Raises:
        FileNotFoundError: When no such batch is pending.
    """
    with locked(data_fol, WORK_SUBDIR):
        path = work_dir(data_fol, WORK_SUBDIR) / f"{batch}.jsonl"
        if not path.exists():
            msg = f"no pending batch {batch} under {path.parent}"
            raise FileNotFoundError(msg)
        items = read_jsonl(GlossWriteItem, path)
        glosses = parse_glosses(batch, text, items)
        rows = [
            GlossProposal(
                concept_id=item.concept_id,
                language=LANGUAGE,
                current_definition="",
                proposed_definition=glosses[item.n],
                status="proposed",
            )
            for item in items
        ]
        log = GlossWriteLogRow(
            batch=batch,
            rules_sha=guide_sha(rules_path),
            applied_at=datetime.now(UTC).isoformat(timespec="seconds"),
            items=len(rows),
            keys=[item.key for item in items],
        )
        append_rows(curated_path(data_fol, GLOSS_BACKFILL_FILE), rows)
        append_rows(curated_path(data_fol, LOG_FILE), [log])
        path.unlink()
        lg.info("Applied batch {}: {} gloss(es)", batch, len(rows))
        return log


def correct_gloss(data_fol: Path, key: str, gloss: str) -> GlossProposal:
    """Record a corrected gloss as an accepted override.

    The build applies the first accepted backfill row of a concept, so a second
    backfill row would be skipped; the overrides are applied before the
    backfill and always win.

    Args:
        data_fol: Project data folder.
        key: The backfill key, ``pt:{concept_key}``.
        gloss: The corrected gloss.

    Returns:
        The override row (also appended to the gloss overrides).

    Raises:
        GlossCorrectionError: When no pt backfill row has that key.
    """
    path = curated_path(data_fol, GLOSS_BACKFILL_FILE)
    rows = read_jsonl(GlossProposal, path) if path.exists() else []
    written = [
        row
        for row in rows
        if row.language == LANGUAGE
        and f"{LANGUAGE}:{concept_key(row.concept_id)}" == key
    ]
    if not written:
        msg = f"no {LANGUAGE} backfill row with key {key}"
        raise GlossCorrectionError(msg)
    override = GlossProposal(
        concept_id=written[-1].concept_id,
        language=LANGUAGE,
        current_definition=written[-1].proposed_definition,
        proposed_definition=gloss,
        rationale="corrected on review",
        status="accepted",
    )
    append_rows(gloss_overrides_path(data_fol), [override])
    lg.info("Corrected {}: {!r}", key, gloss)
    return override


def write_status(data_fol: Path) -> GlossWriteStatus:
    """Return the progress of the agent batches."""
    pending = _pending(data_fol)
    logs = _log_rows(data_fol)
    return GlossWriteStatus(
        left=len(_todo(data_fol, pending, logs)),
        pending=sorted(pending),
        batches=len(logs),
        written=sum(row.items for row in logs),
    )
