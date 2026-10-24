"""Review the look-alike candidates in batches through the agent harness (phase 11).

The deterministic generator (`lookalikes`) selects about 65k look-alike pairs.
Instead of a paid LLM verifier, a reviewing agent (a Claude Code session or one
of its subagents, following ``.claude/skills/lookalike-review/``) labels them a
batch at a time, against the written rules in ``docs/guides/lookalike_review.md``.

Worklist:
    `build_worklist` orders every selected candidate by usefulness to a learner,
    in tiers worked through one after the other:

    - ``A``: the target word is very common (Zipf 4.5 or more).
    - ``B``: likely traps: a near-identical or same-key pair whose meanings look
      different to the generator, with a target word of Zipf 2.5 or more; the
      most common known words come first, since they mislead the most.
    - ``C``: the rest of the common target words (Zipf 3.5 to 4.5).
    - ``D``: everyday target words (Zipf 2.5 to 3.5).
    - ``E``: the rare tail.

    Gold pairs are already labelled and stay out of the worklist.

Batches:
    `serve_batch` reserves the next unreviewed items and mixes in a few hidden
    gold pairs, which measure the reviewer's agreement batch by batch.
    `apply_batch` validates the reviewer's labels (every item, a legal kind, a
    note on every false friend). The verdicts then go into
    ``data/curated/lookalikes.jsonl`` as accepted rows (``unrelated`` as
    rejected, so they are never served again), tagged `REVIEW_MODEL`, the batch
    id and the guide's hash. The batch's numbers go to
    ``data/curated/lookalike_review_log.jsonl``.

Label format:
    One line per item: ``N K`` where ``K`` is ``c`` (cognate), ``p`` (partial),
    ``f`` (full) or ``u`` (unrelated). A ``p`` or ``f`` line carries the learner
    note after the letter. A ``!`` right after the letter marks an edge case:
    the call is applied, and listed for a second look::

        1 c
        2 u
        3 f pt "parentes" means relatives; en "parents" is "pais"
        4 p! pt "turno" is mostly a work shift; en "turn" is mostly "vez"
"""

from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
import fcntl
import hashlib
import random
import re
from typing import TYPE_CHECKING
from typing import Literal

from loguru import logger as lg
from pydantic import BaseModel
from pydantic import Field

from lang_tools.lexicon.codec import LEXICON_SUBDIR
from lang_tools.lexicon.ingestion.lookalikes import LOOKALIKES_FILE
from lang_tools.lexicon.ingestion.lookalikes import REVIEW_MODEL
from lang_tools.lexicon.ingestion.lookalikes import LookalikeProposal
from lang_tools.lexicon.ingestion.lookalikes import load_gold
from lang_tools.lexicon.ingestion.lookalikes import sense_summary
from lang_tools.lexicon.lemma_store import CorpusNotFoundError
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import read_jsonl
from lang_tools.lexicon.quality import _connect
from lang_tools.lexicon.quality import _table_sources
from lang_tools.lexicon.relations import (
    LookalikeKind,  # noqa: TC001 - pydantic needs it at runtime
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from collections.abc import Mapping
    from collections.abc import Sequence
    from pathlib import Path

    from lang_tools.lexicon.ingestion.lookalikes import GoldPair
    from lang_tools.lexicon.ingestion.lookalikes import LookalikeCandidate
    from lang_tools.lexicon.lemma_store import LexiconStore

#: The committed, ordered worklist, under ``data/curated/``.
WORKLIST_FILE = "lookalike_worklist.jsonl"
#: One row per applied batch, under ``data/curated/``.
REVIEW_LOG_FILE = "lookalike_review_log.jsonl"
#: Served, not yet applied batches live here, under the data folder (not committed).
WORK_SUBDIR = "work/lookalike_review"
#: Items per batch, and hidden gold pairs mixed into each.
DEFAULT_BATCH_SIZE = 100
DEFAULT_GOLD_PER_BATCH = 5
#: Characters of sense summary shown per side.
_TARGET_SENSES_SHOWN = 110
_KNOWN_SENSES_SHOWN = 90

Tier = Literal["A", "B", "C", "D", "E"]
TIERS: tuple[Tier, ...] = ("A", "B", "C", "D", "E")
#: Target-word Zipf floors of the frequency tiers.
TIER_A_ZIPF = 4.5
TIER_C_ZIPF = 3.5
TIER_D_ZIPF = 2.5
#: A generator pair this close in form counts as a likely trap for tier B.
TIER_B_FORM_SIMILARITY = 0.85

#: Label letters -> verdicts.
LABEL_KINDS: dict[str, Literal["full", "partial", "cognate", "unrelated"]] = {
    "c": "cognate",
    "p": "partial",
    "f": "full",
    "u": "unrelated",
}
_LABEL_RE = re.compile(r"^\s*(\d+)\s+([cpfu])(!?)(?:\s+(.*?))?\s*$")


class WorkItem(BaseModel):
    """One candidate pair of the ordered worklist.

    Attributes:
        rank: Position in the worklist (0 is reviewed first).
        tier: The usefulness tier (see the module docstring).
        target_id: Lemma id on the learned side.
        target_text: Its form.
        known_id: Lemma id on the known side.
        known_text: Its form.
        known_language: The known side's language.
        provisional: The generator's provisional kind (never shown to the
            reviewer, to avoid anchoring).
        similarity: The generator's similarity score.
        target_zipf: Highest token frequency of the target lemma.
        known_zipf: Highest token frequency of the known lemma.
    """

    rank: int
    tier: Tier
    target_id: str
    target_text: str
    known_id: str
    known_text: str
    known_language: str
    provisional: LookalikeKind
    similarity: float
    target_zipf: float | None = None
    known_zipf: float | None = None

    @property
    def key(self) -> str:
        """Return the item key, ``{target_id}:{known_id}``."""
        return f"{self.target_id}:{self.known_id}"


def tier_of(candidate: LookalikeCandidate, target_zipf: float | None) -> Tier:
    """Return the usefulness tier of a candidate (see the module docstring)."""
    zipf = target_zipf or 0.0
    if zipf >= TIER_A_ZIPF:
        return "A"
    looks_trap = candidate.kind != "cognate" and (
        candidate.same_key or candidate.form_similarity >= TIER_B_FORM_SIMILARITY
    )
    if looks_trap and zipf >= TIER_D_ZIPF:
        return "B"
    if zipf >= TIER_C_ZIPF:
        return "C"
    if zipf >= TIER_D_ZIPF:
        return "D"
    return "E"


def build_worklist(
    candidates: Sequence[LookalikeCandidate],
    target_zipf: Mapping[str, float],
    *,
    skip: set[str] | None = None,
) -> list[WorkItem]:
    """Order the candidates for review, by tier then usefulness.

    Within a tier the most frequent target words come first; tier B leads with
    the most frequent known words instead, since those are the ones that
    mislead. Ties break on the item key, so the order is deterministic.

    Args:
        candidates: The selected candidates (`select_candidates`).
        target_zipf: Target lemma id -> highest token frequency (Zipf).
        skip: Item keys to leave out (the gold pairs, already labelled).

    Returns:
        The worklist, ranked from 0.
    """
    skip = skip or set()

    def order(item: tuple[Tier, LookalikeCandidate, float | None]) -> tuple:
        tier, cand, zipf = item
        target = -(zipf or 0.0)
        known = -(cand.known_zipf or 0.0)
        first, second = (known, target) if tier == "B" else (target, known)
        return TIERS.index(tier), first, second, cand.key

    rows: list[tuple[Tier, LookalikeCandidate, float | None]] = [
        (
            tier_of(cand, target_zipf.get(cand.target_id)),
            cand,
            target_zipf.get(cand.target_id),
        )
        for cand in candidates
        if cand.key not in skip
    ]
    rows.sort(key=order)
    return [
        WorkItem(
            rank=rank,
            tier=tier,
            target_id=cand.target_id,
            target_text=cand.target_text,
            known_id=cand.known_id,
            known_text=cand.known_text,
            known_language=cand.known_language,
            provisional=cand.kind,
            similarity=round(cand.similarity, 4),
            target_zipf=zipf,
            known_zipf=cand.known_zipf,
        )
        for rank, (tier, cand, zipf) in enumerate(rows)
    ]


def lemma_frequencies(data_fol: Path) -> dict[str, float]:
    """Return lemma id -> highest token frequency (Zipf) over its senses.

    Raises:
        CorpusNotFoundError: When no Parquet corpus exists at the location.
    """
    corpus_dir = data_fol / LEXICON_SUBDIR
    if not (corpus_dir / "concepts.parquet").exists():
        raise CorpusNotFoundError(corpus_dir)
    senses = _table_sources(data_fol)["senses"]
    con = _connect()
    try:
        rows = con.execute(
            f"SELECT lemma_id, max(token_frequency) FROM {senses} "  # noqa: S608 - internal source
            "WHERE token_frequency IS NOT NULL GROUP BY lemma_id",
        ).fetchall()
    finally:
        con.close()
    return {lemma_id: float(zipf) for lemma_id, zipf in rows}


def gold_key(pair: GoldPair) -> str:
    """Return a gold pair's item key, ``{pt_lemma_id}:{other_lemma_id}``."""
    return f"{pair.pt_lemma_id}:{pair.other_lemma_id}"


def load_worklist(data_fol: Path) -> list[WorkItem]:
    """Read the committed worklist (empty when it does not exist)."""
    path = curated_path(data_fol, WORKLIST_FILE)
    return read_jsonl(WorkItem, path) if path.exists() else []


class BatchItem(BaseModel):
    """One item of a served batch.

    Attributes:
        n: The item's number in the batch, as the reviewer sees it.
        key: ``{target_id}:{known_id}``.
        target_text: The learned-side form.
        known_text: The known-side form.
        known_language: The known side's language.
        target_senses: Sense summary of the target lemma.
        known_senses: Sense summary of the known lemma.
        rank: Worklist rank, or None for a hidden gold item.
        gold_kind: The gold label of a hidden gold item (``noise`` reads as
            ``unrelated``); None for a worklist item.
        similarity: The generator's similarity score (worklist items).
    """

    n: int
    key: str
    target_text: str
    known_text: str
    known_language: str
    target_senses: str = ""
    known_senses: str = ""
    rank: int | None = None
    gold_kind: str | None = None
    similarity: float | None = None


class ReviewLogRow(BaseModel):
    """The numbers of one applied batch (a line of the review log).

    Attributes:
        batch: The batch id.
        tier: The tier(s) the batch was drawn from, e.g. ``A``.
        items: Worklist items labelled.
        kinds: Verdict -> count, over the worklist items.
        edge_cases: Worklist items flagged as edge cases.
        gold_keys: The hidden gold items' keys.
        gold_agree: Hidden gold items the reviewer labelled like the gold set.
        gold_misses: ``"pt / other: gold -> label"`` for each disagreement.
        guide_sha: Hash of the review guide the batch was labelled against.
    """

    batch: str
    tier: str
    items: int
    kinds: dict[str, int] = Field(default_factory=dict)
    edge_cases: int = 0
    gold_keys: list[str] = Field(default_factory=list)
    gold_agree: int = 0
    gold_misses: list[str] = Field(default_factory=list)
    guide_sha: str = ""


class LabelError(ValueError):
    """The reviewer's labels for a batch do not validate."""

    def __init__(self, batch: str, problems: Sequence[str]) -> None:
        """Keep the problems, and list them in the message."""
        self.problems = list(problems)
        super().__init__(
            f"batch {batch}: {len(self.problems)} problem(s): "
            + "; ".join(self.problems)
        )


class Label(BaseModel):
    """One parsed label line.

    Attributes:
        kind: The verdict.
        note: The learner note (false friends).
        edge_case: Flagged with ``!``.
    """

    kind: Literal["full", "partial", "cognate", "unrelated"]
    note: str = ""
    edge_case: bool = False


def parse_labels(batch: str, text: str, numbers: Sequence[int]) -> dict[int, Label]:
    """Parse and validate a batch's label lines.

    Args:
        batch: The batch id (for the error message).
        text: The label lines (see the module docstring); blank lines and ``#``
            comments are ignored.
        numbers: The item numbers the batch served.

    Returns:
        Item number -> label.

    Raises:
        LabelError: Listing every unparseable line, unknown or repeated
            number, missing item and false friend without a note.
    """
    expected = set(numbers)
    labels: dict[int, Label] = {}
    problems: list[str] = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = _LABEL_RE.match(line)
        if not match:
            problems.append(f"unparseable line {line.strip()!r}")
            continue
        n, letter, bang, note = (
            int(match[1]),
            match[2],
            match[3],
            (match[4] or "").strip(),
        )
        if n not in expected:
            problems.append(f"item {n} is not in the batch")
        elif n in labels:
            problems.append(f"item {n} is labelled twice")
        kind = LABEL_KINDS[letter]
        if kind in {"full", "partial"} and not note:
            problems.append(f"item {n} is {kind} but has no note")
        labels[n] = Label(
            kind=kind,
            note=note if kind in {"full", "partial"} else "",
            edge_case=bool(bang),
        )
    missing = sorted(expected - set(labels))
    if missing:
        problems.append(f"missing item(s) {', '.join(map(str, missing))}")
    if problems:
        raise LabelError(batch, problems)
    return labels


def guide_sha(guide_path: Path) -> str:
    """Return a short hash of the review guide, for provenance."""
    return (
        hashlib.sha256(guide_path.read_bytes()).hexdigest()[:12]
        if guide_path.exists()
        else ""
    )


def _work_dir(data_fol: Path) -> Path:
    path = data_fol / WORK_SUBDIR
    path.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def _locked(data_fol: Path) -> Iterator[None]:
    """Serialize reservations and applies across concurrent reviewers."""
    with (_work_dir(data_fol) / ".lock").open("w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _reviewed_keys(data_fol: Path) -> set[str]:
    path = curated_path(data_fol, LOOKALIKES_FILE)
    rows = read_jsonl(LookalikeProposal, path) if path.exists() else []
    return {f"{row.target_id}:{row.known_id}" for row in rows}


def _log_rows(data_fol: Path) -> list[ReviewLogRow]:
    path = curated_path(data_fol, REVIEW_LOG_FILE)
    return read_jsonl(ReviewLogRow, path) if path.exists() else []


def _pending(data_fol: Path) -> dict[str, list[BatchItem]]:
    return {
        path.stem: read_jsonl(BatchItem, path)
        for path in sorted(_work_dir(data_fol).glob("*.jsonl"))
    }


def _append(path: Path, rows: Sequence[BaseModel]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.writelines(row.model_dump_json() + "\n" for row in rows)


def _write_batch(
    data_fol: Path,
    store: LexiconStore,
    *,
    batch: str,
    picked: Sequence[WorkItem],
    gold_per_batch: int,
) -> list[BatchItem]:
    """Mix hidden gold into ``picked``, shuffle, and write the batch file.

    Must run under `_locked`.
    """
    pending = _pending(data_fol)
    rng = random.Random(batch)  # noqa: S311 - a reproducible shuffle, not crypto
    used_gold = {key for row in _log_rows(data_fol) for key in row.gold_keys} | {
        item.key for items in pending.values() for item in items if item.gold_kind
    }
    gold_pool = [
        pair for pair in load_gold(data_fol) if gold_key(pair) not in used_gold
    ]
    gold = rng.sample(gold_pool, min(gold_per_batch, len(gold_pool)))
    entries: list[tuple[str, str, str, str, int | None, str | None, float | None]] = [
        (
            it.key,
            it.target_text,
            it.known_text,
            it.known_language,
            it.rank,
            None,
            it.similarity,
        )
        for it in picked
    ]
    entries += [
        (gold_key(g), g.pt, g.other, g.other_language, None, g.kind, None) for g in gold
    ]
    rng.shuffle(entries)
    items = []
    for n, (key, target, known, language, rank, gold_kind, similarity) in enumerate(
        entries, start=1
    ):
        target_id, known_id = key.split(":")
        items.append(
            BatchItem(
                n=n,
                key=key,
                target_text=target,
                known_text=known,
                known_language=language,
                target_senses=sense_summary(store, target_id)[:_TARGET_SENSES_SHOWN],
                known_senses=sense_summary(store, known_id)[:_KNOWN_SENSES_SHOWN],
                rank=rank,
                gold_kind=gold_kind,
                similarity=similarity,
            )
        )
    _append(_work_dir(data_fol) / f"{batch}.jsonl", items)
    return items


def recheck_batch(
    data_fol: Path,
    store: LexiconStore,
    *,
    batch: str,
    keys: Sequence[str],
    guide_path: Path,
    size: int = DEFAULT_BATCH_SIZE,
    gold_per_batch: int = DEFAULT_GOLD_PER_BATCH,
) -> list[BatchItem]:
    """Serve already reviewed pairs again, for a re-check under the current guide.

    Picks the next ``size`` of ``keys`` (``{target_id}:{known_id}``) that are on
    the worklist, not pending, and whose latest review row was not written
    under the current guide. `apply_batch` then appends new rows, and the
    corpus build keeps the later row of a pair.

    Args:
        data_fol: Project data folder.
        store: The lexicon store, for the sense summaries.
        batch: The batch id (e.g. ``r0001``).
        keys: The pairs to re-check, in the order to serve them.
        guide_path: The review guide; rows already under its hash are skipped.
        size: Pairs to reserve.
        gold_per_batch: Hidden gold pairs to mix in.

    Returns:
        The batch items (empty when every key is re-checked or pending).
    """
    with _locked(data_fol):
        pending = _pending(data_fol)
        if batch in pending:
            return pending[batch]
        if any(row.batch == batch for row in _log_rows(data_fol)):
            msg = f"batch {batch} was already applied"
            raise ValueError(msg)
        sha = guide_sha(guide_path)
        path = curated_path(data_fol, LOOKALIKES_FILE)
        latest = {
            f"{row.target_id}:{row.known_id}": row.prompt_sha
            for row in (read_jsonl(LookalikeProposal, path) if path.exists() else [])
        }
        busy = {item.key for items in pending.values() for item in items}
        by_key = {item.key: item for item in load_worklist(data_fol)}
        picked = [
            by_key[key]
            for key in keys
            if key in by_key and key not in busy and latest.get(key) != sha
        ][:size]
        if not picked:
            return []
        items = _write_batch(
            data_fol, store, batch=batch, picked=picked, gold_per_batch=gold_per_batch
        )
        lg.info("Served re-check batch {}: {} item(s)", batch, len(picked))
        return items


def serve_batch(
    data_fol: Path,
    store: LexiconStore,
    *,
    batch: str,
    size: int = DEFAULT_BATCH_SIZE,
    tier: Tier | None = None,
    gold_per_batch: int = DEFAULT_GOLD_PER_BATCH,
) -> list[BatchItem]:
    """Reserve the next unreviewed worklist items as a batch, with hidden gold.

    The batch is written under the work folder, so concurrent reviewers never
    get the same items, and `apply_batch` can check the labels against it.
    Serving an id that is already pending returns that batch unchanged.

    Args:
        data_fol: Project data folder.
        store: The lexicon store, for the sense summaries.
        batch: The batch id (e.g. ``a0001``).
        size: Worklist items to reserve.
        tier: Only draw from this tier (default: the first tier with work left).
        gold_per_batch: Hidden gold pairs to mix in.

    Returns:
        The batch items, in the order the reviewer sees them (empty when the
        worklist, or the tier, is done).
    """
    with _locked(data_fol):
        pending = _pending(data_fol)
        if batch in pending:
            return pending[batch]
        if any(row.batch == batch for row in _log_rows(data_fol)):
            msg = f"batch {batch} was already applied"
            raise ValueError(msg)
        taken = _reviewed_keys(data_fol) | {
            item.key for items in pending.values() for item in items
        }
        todo = [item for item in load_worklist(data_fol) if item.key not in taken]
        if tier is None and todo:
            tier = todo[0].tier
        picked = [item for item in todo if item.tier == tier][:size]
        if not picked:
            return []
        items = _write_batch(
            data_fol, store, batch=batch, picked=picked, gold_per_batch=gold_per_batch
        )
        lg.info(
            "Served batch {}: {} item(s) of tier {} + {} gold",
            batch,
            len(picked),
            tier,
            len(items) - len(picked),
        )
        return items


def render_batch(items: Sequence[BatchItem]) -> str:
    """Return the batch as the compact lines a reviewer reads (gold looks the same)."""
    return "\n".join(
        f"{it.n} {it.known_language} | {it.target_text} [{it.target_senses}]"
        f" | {it.known_text} [{it.known_senses}]"
        for it in items
    )


def apply_batch(
    data_fol: Path,
    batch: str,
    labels_text: str,
    *,
    guide_path: Path,
) -> ReviewLogRow:
    """Validate a batch's labels and record them.

    Worklist items become `LookalikeProposal` rows (accepted, or rejected for
    ``unrelated``) appended to ``lookalikes.jsonl``; hidden gold items only
    count toward the agreement. Nothing is written when a label is invalid.

    Args:
        data_fol: Project data folder.
        batch: The served batch id.
        labels_text: The reviewer's label lines.
        guide_path: The review guide, hashed into every row.

    Returns:
        The batch's log row (also appended to the review log).

    Raises:
        LabelError: When the labels do not validate.
        FileNotFoundError: When no such batch is pending.
    """
    with _locked(data_fol):
        path = _work_dir(data_fol) / f"{batch}.jsonl"
        if not path.exists():
            msg = f"no pending batch {batch} under {path.parent}"
            raise FileNotFoundError(msg)
        items = read_jsonl(BatchItem, path)
        labels = parse_labels(batch, labels_text, [it.n for it in items])
        sha = guide_sha(guide_path)
        rows: list[LookalikeProposal] = []
        kinds: Counter[str] = Counter()
        gold_keys: list[str] = []
        misses: list[str] = []
        edge_cases = 0
        ranks = {item.rank for item in items if item.rank is not None}
        worklist = {
            item.rank: item for item in load_worklist(data_fol) if item.rank in ranks
        }
        for item in items:
            label = labels[item.n]
            if item.gold_kind is not None:
                gold_keys.append(item.key)
                expected = "unrelated" if item.gold_kind == "noise" else item.gold_kind
                if label.kind != expected:
                    pair = f"{item.target_text} / {item.known_text}"
                    misses.append(f"{pair}: {expected} -> {label.kind}")
                continue
            target_id, known_id = item.key.split(":")
            kinds[label.kind] += 1
            edge_cases += label.edge_case
            rows.append(
                LookalikeProposal(
                    target_id=target_id,
                    target_text=item.target_text,
                    known_id=known_id,
                    known_text=item.known_text,
                    known_language=item.known_language,
                    kind=label.kind,
                    note=label.note,
                    similarity=item.similarity,
                    status="rejected" if label.kind == "unrelated" else "accepted",
                    model=REVIEW_MODEL,
                    prompt_sha=sha,
                    batch=batch,
                    edge_case=label.edge_case,
                )
            )
        batch_tiers = sorted(
            {worklist[it.rank].tier for it in items if it.rank in worklist}
        )
        log = ReviewLogRow(
            batch=batch,
            tier="".join(batch_tiers),
            items=len(rows),
            kinds=dict(kinds),
            edge_cases=edge_cases,
            gold_keys=gold_keys,
            gold_agree=len(gold_keys) - len(misses),
            gold_misses=misses,
            guide_sha=sha,
        )
        _append(curated_path(data_fol, LOOKALIKES_FILE), rows)
        _append(curated_path(data_fol, REVIEW_LOG_FILE), [log])
        path.unlink()
        lg.info(
            "Applied batch {}: {} row(s), gold {}/{}",
            batch,
            len(rows),
            log.gold_agree,
            len(gold_keys),
        )
        return log


def gold_proposals(gold: Sequence[GoldPair]) -> list[LookalikeProposal]:
    """Turn the gold set into look-alike rows (the hand-written labels apply as-is)."""
    return [
        LookalikeProposal(
            target_id=pair.pt_lemma_id,
            target_text=pair.pt,
            known_id=pair.other_lemma_id,
            known_text=pair.other,
            known_language=pair.other_language,
            kind="unrelated" if pair.kind == "noise" else pair.kind,
            note=pair.reason if pair.kind in {"full", "partial"} else "",
            status="rejected" if pair.kind == "noise" else "accepted",
            model="manual",
            batch="gold",
        )
        for pair in gold
    ]


def import_gold(data_fol: Path) -> int:
    """Append the gold pairs not yet in ``lookalikes.jsonl``; return how many."""
    with _locked(data_fol):
        present = _reviewed_keys(data_fol)
        rows = [
            row
            for row in gold_proposals(load_gold(data_fol))
            if f"{row.target_id}:{row.known_id}" not in present
        ]
        _append(curated_path(data_fol, LOOKALIKES_FILE), rows)
        return len(rows)


class ReviewStatus(BaseModel):
    """Progress of the review.

    Attributes:
        tiers: Tier -> ``(reviewed, total)`` worklist items.
        pending: Served batch ids not yet applied.
        batches: Applied batches.
        gold_agree: Hidden gold items labelled like the gold set, over all batches.
        gold_total: Hidden gold items served in applied batches.
        edge_cases: Worklist items flagged as edge cases.
    """

    tiers: dict[str, tuple[int, int]]
    pending: list[str]
    batches: int
    gold_agree: int
    gold_total: int
    edge_cases: int


def review_status(data_fol: Path) -> ReviewStatus:
    """Return how far the review has come, per tier."""
    reviewed = _reviewed_keys(data_fol)
    totals: Counter[str] = Counter()
    done: Counter[str] = Counter()
    for item in load_worklist(data_fol):
        totals[item.tier] += 1
        done[item.tier] += item.key in reviewed
    log = _log_rows(data_fol)
    return ReviewStatus(
        tiers={tier: (done[tier], totals[tier]) for tier in TIERS if totals[tier]},
        pending=sorted(_pending(data_fol)),
        batches=len(log),
        gold_agree=sum(row.gold_agree for row in log),
        gold_total=sum(len(row.gold_keys) for row in log),
        edge_cases=sum(row.edge_cases for row in log),
    )
