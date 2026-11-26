"""Pick what a false friend's look-alike mainly means, through the agent harness.

A drill that asks a pt word in English can trap a learner who reads it through
Italian: pt *bravo* is "angry", it *bravo* is "good", so *good* is the trap. The
card's look-alike hints carry the look-alike's best-sense words for that
(`LookalikeHint.means`), and the best sense of an en or it word is picked by
frequency, then concept commonness. Italian senses tie on frequency, so
commonness alone picks, and it *dito* shows "toe". A reviewing agent (a Claude
Code session or one of its subagents, following
``.claude/skills/false-friend-meaning-review/``) reads each look-alike with all
its senses, against the rules in ``docs/guides/false_friend_meaning_review.md``,
and picks the sense a speaker of that language means first.

Worklist:
    `build_worklist` lists the en and it lemmas that are a full or partial false
    friend of a pt card and have two or more senses (a one-sense word has
    nothing to pick), the gold lemmas first, then the rest by their card
    frequency; it is stored under the work folder, which is not committed, and
    rebuilt from the corpus.

Batches:
    `serve_batch` reserves the next unlabelled lemmas, with their senses and the
    pt words they are a false friend of. `apply_batch` validates the labels and
    records them:

    - every label gets a `MeaningLogRow` in
      ``data/curated/false_friend_meaning_log.jsonl``, with the concept the
      label chose (sense 1 for a keep);
    - every label gets a `BestSense` row in ``data/curated/best_senses.jsonl``,
      the file the sense review writes too: the pinned sense for ``pK``, no
      concept for ``k`` and ``m`` (keep the frequency pick, and retract an
      earlier pin).

    `gold_agreement` compares the latest labels of the gold lemmas with
    ``data/curated/false_friend_meaning_gold.jsonl``.

Label format:
    One line per item: the item number, the label, an optional ``!`` right after
    it for an edge case, and a reason after ``#``. Senses are numbered in the
    card's pick order, so sense 1 is the current pick. ``k`` keeps it; ``pK``
    pins sense K (K of 2 or more); ``m`` says the main meaning is not among the
    senses, and needs a reason. Blank lines and lines starting with ``#`` are
    ignored::

        1 k
        2 p3
        3 p2! # the finger; "toe" is the dito del piede
        4 m # the main meaning, a typeface, has no sense here
"""

from __future__ import annotations

from collections import Counter
import re
from typing import TYPE_CHECKING
from typing import Literal

from loguru import logger as lg
from pydantic import BaseModel
from pydantic import Field

from lang_tools.lexicon.card import MAX_CARD_LIMIT
from lang_tools.lexicon.card import CardQuery
from lang_tools.lexicon.concept_id import concept_key
from lang_tools.lexicon.ingestion.best_senses import BEST_SENSES_FILE
from lang_tools.lexicon.ingestion.best_senses import BestSense
from lang_tools.lexicon.ingestion.lookalikes import REVIEW_MODEL
from lang_tools.lexicon.ingestion.review_batches import LabelError
from lang_tools.lexicon.ingestion.review_batches import append_rows
from lang_tools.lexicon.ingestion.review_batches import guide_sha
from lang_tools.lexicon.ingestion.review_batches import locked
from lang_tools.lexicon.ingestion.review_batches import work_dir
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import read_jsonl
from lang_tools.lexicon.maintenance import write_jsonl
from lang_tools.lexicon.relations import FALSE_FRIEND_KINDS

if TYPE_CHECKING:
    from collections.abc import Collection
    from collections.abc import Sequence
    from pathlib import Path

    from lang_tools.lexicon.lemma_store import LexiconStore

#: Every label, one per lemma.
Label = Literal["k", "p", "m"]

#: The ordered worklist, under the data folder (rebuilt from the corpus).
WORKLIST_FILE = "work/false_friend_meaning_worklist.jsonl"
#: One row per labelled lemma, under ``data/curated/``.
REVIEW_LOG_FILE = "false_friend_meaning_log.jsonl"
#: The hand-checked gold lemmas, under ``data/curated/``.
GOLD_FILE = "false_friend_meaning_gold.jsonl"
#: Served, not yet applied batches live here, under the data folder (not committed).
WORK_SUBDIR = "work/false_friend_meaning_review"
#: Items per batch.
DEFAULT_BATCH_SIZE = 100
#: The pt cards' language, and the languages whose look-alikes are reviewed.
CARD_LANGUAGE = "pt"
KNOWN_LANGUAGES = ("en", "it")
#: Characters of gloss and words per language shown per sense.
_GLOSS_SHOWN = 100
_WORDS_SHOWN = 5

_LABEL_RE = re.compile(r"^(k|m|p(\d+))(!?)$")


class UnknownRecheckWordError(LookupError):
    """Raised when a re-check names a lemma the review never labelled."""

    def __init__(self, words: Sequence[str]) -> None:
        """Initialize with the words that have no label.

        Args:
            words: The unknown ``language:text`` words.
        """
        self.words = list(words)
        super().__init__(f"no label to re-check for: {', '.join(self.words)}")


class MeaningWorkItem(BaseModel):
    """One lemma of the ordered worklist.

    Attributes:
        rank: Position in the worklist (0 is reviewed first).
        lemma_id: The en or it lemma.
        lemma_text: Its form.
        language: Its language.
        sense_frequency: Its card's frequency, which orders the worklist.
    """

    rank: int
    lemma_id: str
    lemma_text: str
    language: str
    sense_frequency: float | None = None


class MeaningGold(BaseModel):
    """One hand-checked lemma of the gold set (a JSONL line).

    Attributes:
        lemma_id: The lemma.
        lemma_text: Its form.
        language: Its language.
        best: The concept keys a right label may choose; empty when the main
            meaning is not among the senses (a right label is ``m``).
        reason: Why, for the human reading a miss.
    """

    lemma_id: str
    lemma_text: str
    language: str
    best: list[str] = Field(default_factory=list)
    reason: str = ""


class SenseChoice(BaseModel):
    """One sense of a served lemma, as the reviewer sees it.

    Attributes:
        concept_key: The sense's concept (`concept_key`).
        gloss: The concept's English gloss.
        words: The concept's words per language, the lemma itself left out.
    """

    concept_key: str
    gloss: str = ""
    words: dict[str, list[str]] = Field(default_factory=dict)


class PtFalseFriend(BaseModel):
    """A pt word the served lemma is a false friend of.

    Attributes:
        text: The pt word.
        kind: ``full`` or ``partial``.
        note: The edge's learner note (English).
    """

    text: str
    kind: str
    note: str = ""


class MeaningBatchItem(BaseModel):
    """One item of a served batch.

    Attributes:
        n: The item's number in the batch, as the reviewer sees it.
        lemma_id: The lemma.
        lemma_text: Its form.
        language: Its language.
        part_of_speech: The lemma's part of speech.
        senses: Every sense, in the card's pick order (sense 1 is the card).
        false_friend_of: The pt words it is a false friend of.
    """

    n: int
    lemma_id: str
    lemma_text: str
    language: str
    part_of_speech: str | None = None
    senses: list[SenseChoice] = Field(default_factory=list)
    false_friend_of: list[PtFalseFriend] = Field(default_factory=list)


class MeaningLabel(BaseModel):
    """One parsed label line.

    Attributes:
        label: ``k``, ``p`` or ``m``.
        sense: The pinned sense number for ``p``; 1 for ``k``; None for ``m``.
        edge_case: The reviewer marked the item with ``!``.
        reason: Why, after ``#``.
    """

    label: Label
    sense: int | None = None
    edge_case: bool = False
    reason: str = ""


class MeaningLogRow(BaseModel):
    """One labelled lemma (a line of the review log).

    Attributes:
        batch: The batch id.
        lemma_id: The lemma.
        language: Its language.
        text: Its form.
        label: ``k``, ``p`` or ``m``.
        sense: The chosen sense's number in the served batch, None for ``m``.
        concept_key: The chosen sense's concept (sense 1 for ``k``), None for
            ``m``.
        edge_case: The reviewer marked the item with ``!``.
        reason: The reviewer's reason.
        rulebook_sha: Hash of the rulebook the batch was labelled against.
    """

    batch: str
    lemma_id: str
    language: str
    text: str
    label: Label
    sense: int | None = None
    concept_key: str | None = None
    edge_case: bool = False
    reason: str = ""
    rulebook_sha: str = ""


class GoldAgreement(BaseModel):
    """How the latest labels of the gold lemmas compare with the gold set.

    Attributes:
        labelled: Gold lemmas with a label.
        agree: Labels that chose a gold concept (or ``m`` where gold has none).
        misses: ``"language text: gold -> chosen"`` for each disagreement.
    """

    labelled: int
    agree: int
    misses: list[str] = Field(default_factory=list)


class MeaningStatus(BaseModel):
    """Progress of the review.

    Attributes:
        worklist: Lemmas on the worklist.
        labelled: Worklist lemmas with a label.
        labels: Label -> lemmas with it (latest label per lemma).
        pending: Served batch ids not yet applied.
        batches: Applied batches.
    """

    worklist: int
    labelled: int
    labels: dict[str, int]
    pending: list[str]
    batches: int


def load_gold(data_fol: Path) -> list[MeaningGold]:
    """Read the gold set (empty when it does not exist)."""
    path = curated_path(data_fol, GOLD_FILE)
    return read_jsonl(MeaningGold, path) if path.exists() else []


def build_worklist(
    store: LexiconStore, *, gold_ids: Collection[str] = ()
) -> list[MeaningWorkItem]:
    """Return the en and it false friends of pt cards with two or more senses.

    The pt cards come from trap card queries in pages of `MAX_CARD_LIMIT`, every
    part of speech and inflected forms included, so every full or partial edge
    of the corpus is reached. A lemma that is the false friend of several pt
    words is listed once.

    Args:
        store: The lexicon store.
        gold_ids: Gold lemma ids, put first so the first batch holds them.

    Returns:
        The worklist, ranked from 0: gold lemmas first, then by card frequency,
        most frequent first.
    """
    taken: list[str] = []
    found: dict[str, MeaningWorkItem] = {}
    while True:
        page = store.lemma_cards(
            CardQuery(
                language=CARD_LANGUAGE,
                known_languages=list(KNOWN_LANGUAGES),
                lookalike="trap",
                exclude_part_of_speech=[],
                include_forms=True,
                order="frequency",
                exclude_ids=taken,
                limit=MAX_CARD_LIMIT,
            )
        )
        if not page:
            break
        for card in page:
            taken.append(card.lemma.id)
            for other, _ in store.get_lookalikes_for_lemma(
                card.lemma.id, languages=KNOWN_LANGUAGES, kinds=FALSE_FRIEND_KINDS
            ):
                if other.id in found or len(store.senses_for_lemma(other.id)) < 2:  # noqa: PLR2004
                    continue
                own = store.lemma_card(other.id)
                found[other.id] = MeaningWorkItem(
                    rank=0,
                    lemma_id=other.id,
                    lemma_text=other.text,
                    language=other.language,
                    sense_frequency=own.sense_frequency if own else None,
                )
    gold = set(gold_ids)
    ordered = sorted(
        found.values(),
        key=lambda item: (
            item.lemma_id not in gold,
            -(item.sense_frequency or 0.0),
            item.language,
            item.lemma_text,
        ),
    )
    return [item.model_copy(update={"rank": rank}) for rank, item in enumerate(ordered)]


def save_worklist(data_fol: Path, items: Sequence[MeaningWorkItem]) -> Path:
    """Write the worklist under the data folder; return its path."""
    return write_jsonl(items, data_fol / WORKLIST_FILE)


def load_worklist(data_fol: Path) -> list[MeaningWorkItem]:
    """Read the worklist (empty when it does not exist)."""
    path = data_fol / WORKLIST_FILE
    return read_jsonl(MeaningWorkItem, path) if path.exists() else []


def parse_labels(
    batch: str, text: str, senses_per_item: dict[int, int]
) -> dict[int, MeaningLabel]:
    """Parse and validate a batch's label lines.

    Args:
        batch: The batch id (for the error message).
        text: The label lines (see the module docstring); blank lines and ``#``
            comments are ignored.
        senses_per_item: Item number -> how many senses it was served with.

    Returns:
        Item number -> label.

    Raises:
        LabelError: Listing every unparseable line, unknown or repeated number,
            unknown label, sense number out of range, ``m`` with no reason, and
            missing item.
    """
    labels: dict[int, MeaningLabel] = {}
    problems: list[str] = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        n, label, problem = _parse_line(line, senses_per_item)
        if problem:
            problems.append(problem)
        if n is None or label is None:
            continue
        if n in labels:
            problems.append(f"item {n} is labelled twice")
        labels[n] = label
    missing = sorted(set(senses_per_item) - set(labels))
    if missing:
        problems.append(f"missing item(s) {', '.join(map(str, missing))}")
    if problems:
        raise LabelError(batch, problems)
    return labels


def _parse_line(
    line: str, senses_per_item: dict[int, int]
) -> tuple[int | None, MeaningLabel | None, str]:
    """Parse one label line into its item number, label and problem, if any."""
    body, _, reason = line.partition("#")
    words = body.split()
    if not words or not words[0].isdigit():
        return None, None, f"unparseable line {line.strip()!r}"
    n = int(words[0])
    if n not in senses_per_item:
        return None, None, f"item {n} is not in the batch"
    match = _LABEL_RE.match(words[1]) if len(words) == 2 else None  # noqa: PLR2004
    if match is None:
        return None, None, f"item {n} has no known label in {line.strip()!r}"
    label = MeaningLabel(
        label=match.group(1)[0],  # type: ignore[arg-type]
        sense=int(match.group(2)) if match.group(2) else None,
        edge_case=match.group(3) == "!",
        reason=reason.strip(),
    )
    if label.label == "k":
        label.sense = 1
    problem = ""
    if label.label == "m" and not label.reason:
        problem = f"item {n}: m needs a reason after #"
    elif label.label == "p" and not 2 <= (label.sense or 0) <= senses_per_item[n]:  # noqa: PLR2004
        problem = (
            f"item {n}: p{label.sense} is not a sense from 2 to"
            f" {senses_per_item[n]} (sense 1 is k)"
        )
    return n, None if problem else label, problem


def _log_rows(data_fol: Path) -> list[MeaningLogRow]:
    path = curated_path(data_fol, REVIEW_LOG_FILE)
    return read_jsonl(MeaningLogRow, path) if path.exists() else []


def _pending(data_fol: Path) -> dict[str, list[MeaningBatchItem]]:
    return {
        path.stem: read_jsonl(MeaningBatchItem, path)
        for path in sorted(work_dir(data_fol, WORK_SUBDIR).glob("*.jsonl"))
    }


def _item(store: LexiconStore, n: int, lemma_id: str) -> MeaningBatchItem | None:
    """Return a lemma as a batch item, or None when the corpus no longer has it."""
    lemma = store.get_lemma_by_id(lemma_id)
    if lemma is None:
        return None
    languages = [CARD_LANGUAGE, *KNOWN_LANGUAGES]
    senses = [
        SenseChoice(
            concept_key=concept_key(card.concept_id),
            gloss=(card.gloss or "")[:_GLOSS_SHOWN],
            words={
                language: words[:_WORDS_SHOWN]
                for language in languages
                if (
                    words := [
                        text
                        for text in card.translations.get(language, [])
                        if not (language == lemma.language and text == lemma.text)
                    ]
                )
            },
        )
        for card in store.lemma_sense_cards(lemma_id, translation_languages=languages)
        if card.concept_id is not None
    ]
    false_friend_of = [
        PtFalseFriend(
            text=pt.text, kind=edge.kind, note=edge.explanation_notes.get("en", "")
        )
        for pt, edge in store.get_lookalikes_for_lemma(
            lemma_id, languages=[CARD_LANGUAGE], kinds=FALSE_FRIEND_KINDS
        )
    ]
    return MeaningBatchItem(
        n=n,
        lemma_id=lemma.id,
        lemma_text=lemma.text,
        language=lemma.language,
        part_of_speech=lemma.part_of_speech,
        senses=senses,
        false_friend_of=false_friend_of,
    )


def serve_batch(
    data_fol: Path,
    store: LexiconStore,
    *,
    batch: str,
    size: int = DEFAULT_BATCH_SIZE,
) -> list[MeaningBatchItem]:
    """Reserve the next unlabelled worklist lemmas as a batch.

    The batch is written under the work folder, so concurrent reviewers never
    get the same lemmas, and `apply_batch` can check the labels against the
    senses it showed. Serving an id that is already pending returns that batch
    unchanged. A worklist lemma the corpus no longer has is skipped.

    Args:
        data_fol: Project data folder.
        store: The lexicon store, for the senses.
        batch: The batch id (e.g. ``f0001``).
        size: Lemmas to reserve.

    Returns:
        The batch items (empty when the worklist is done).

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
        taken = {row.lemma_id for row in logs} | {
            item.lemma_id for items in pending.values() for item in items
        }
        items: list[MeaningBatchItem] = []
        for work in load_worklist(data_fol):
            if len(items) == size:
                break
            if work.lemma_id in taken:
                continue
            item = _item(store, len(items) + 1, work.lemma_id)
            if item is not None:
                items.append(item)
        if items:
            append_rows(work_dir(data_fol, WORK_SUBDIR) / f"{batch}.jsonl", items)
            lg.info("Served batch {}: {} lemma(s)", batch, len(items))
        return items


def recheck_batch(
    data_fol: Path,
    store: LexiconStore,
    *,
    batch: str,
    words: Sequence[str],
) -> list[MeaningBatchItem]:
    """Serve already labelled lemmas again, to be labelled anew.

    The batch skips the reservations: its lemmas have a label already, and the
    new one wins when applied. Serving an id that is already pending returns
    that batch unchanged.

    Args:
        data_fol: Project data folder.
        store: The lexicon store, for the senses.
        batch: The batch id (e.g. ``f9001``).
        words: The lemmas as ``language:text`` (en and it share spellings).

    Returns:
        The batch items, in the order of ``words``.

    Raises:
        UnknownRecheckWordError: When a word has no label in the review log, or
            the corpus no longer has it.
    """
    with locked(data_fol, WORK_SUBDIR):
        path = work_dir(data_fol, WORK_SUBDIR) / f"{batch}.jsonl"
        if path.exists():
            return read_jsonl(MeaningBatchItem, path)
        by_word = {
            f"{row.language}:{row.text}": row.lemma_id for row in _log_rows(data_fol)
        }
        missing = [word for word in words if word not in by_word]
        if missing:
            raise UnknownRecheckWordError(missing)
        items: list[MeaningBatchItem] = []
        gone: list[str] = []
        for word in words:
            item = _item(store, len(items) + 1, by_word[word])
            if item is None:
                gone.append(word)
            else:
                items.append(item)
        if gone:
            raise UnknownRecheckWordError(gone)
        append_rows(path, items)
        lg.info("Served re-check {}: {} lemma(s)", batch, len(items))
        return items


def render_batch(items: Sequence[MeaningBatchItem]) -> str:
    """Return the batch as the lines a reviewer reads."""
    lines: list[str] = []
    for item in items:
        pos = f" ({item.part_of_speech})" if item.part_of_speech else ""
        lines.append(f"{item.n} {item.language} {item.lemma_text}{pos}")
        lines += [
            f"  false friend of pt {pt.text} ({pt.kind}): {pt.note}"
            for pt in item.false_friend_of
        ]
        for k, sense in enumerate(item.senses, start=1):
            words = " | ".join(
                f"{language}: {', '.join(texts)}"
                for language, texts in sense.words.items()
            )
            lines.append(f"  {k} {sense.gloss} [{words}]")
    return "\n".join(lines)


def apply_batch(
    data_fol: Path, batch: str, labels_text: str, *, guide_path: Path
) -> list[MeaningLogRow]:
    """Validate a batch's labels and record them; nothing is written if one is bad.

    Args:
        data_fol: Project data folder.
        batch: The served batch id.
        labels_text: The reviewer's label lines.
        guide_path: The rulebook, hashed into every row.

    Returns:
        The log rows written, in item order.

    Raises:
        LabelError: When the labels do not validate.
        FileNotFoundError: When no such batch is pending.
    """
    with locked(data_fol, WORK_SUBDIR):
        path = work_dir(data_fol, WORK_SUBDIR) / f"{batch}.jsonl"
        if not path.exists():
            msg = f"no pending batch {batch} under {path.parent}"
            raise FileNotFoundError(msg)
        items = read_jsonl(MeaningBatchItem, path)
        labels = parse_labels(
            batch, labels_text, {item.n: len(item.senses) for item in items}
        )
        sha = guide_sha(guide_path)
        log: list[MeaningLogRow] = []
        pins: list[BestSense] = []
        for item in items:
            label = labels[item.n]
            chosen = (
                item.senses[label.sense - 1].concept_key
                if label.sense is not None
                else None
            )
            log.append(
                MeaningLogRow(
                    batch=batch,
                    lemma_id=item.lemma_id,
                    language=item.language,
                    text=item.lemma_text,
                    label=label.label,
                    sense=label.sense,
                    concept_key=chosen,
                    edge_case=label.edge_case,
                    reason=label.reason,
                    rulebook_sha=sha,
                )
            )
            pins.append(
                BestSense(
                    lemma_id=item.lemma_id,
                    concept_key=chosen if label.label == "p" else None,
                    lemma_text=item.lemma_text,
                    language=item.language,
                    status="accepted",
                    model=REVIEW_MODEL,
                    prompt_sha=sha,
                    batch=batch,
                    edge_case=label.edge_case,
                )
            )
        append_rows(curated_path(data_fol, BEST_SENSES_FILE), pins)
        append_rows(curated_path(data_fol, REVIEW_LOG_FILE), log)
        path.unlink()
        counts = Counter(row.label for row in log)
        lg.info(
            "Applied batch {}: {} lemma(s) {}",
            batch,
            len(log),
            dict(sorted(counts.items())),
        )
        return log


def gold_agreement(data_fol: Path) -> GoldAgreement:
    """Compare the latest label of each labelled gold lemma with the gold set."""
    latest = {row.lemma_id: row for row in _log_rows(data_fol)}
    agree = 0
    misses: list[str] = []
    labelled = 0
    for gold in load_gold(data_fol):
        row = latest.get(gold.lemma_id)
        if row is None:
            continue
        labelled += 1
        right = row.concept_key in gold.best if gold.best else row.label == "m"
        if right:
            agree += 1
        else:
            want = ", ".join(gold.best) or "m"
            misses.append(
                f"{gold.language} {gold.lemma_text}: {want} -> {row.concept_key or 'm'}"
            )
    return GoldAgreement(labelled=labelled, agree=agree, misses=misses)


def review_status(data_fol: Path) -> MeaningStatus:
    """Return how far the review has come: counts per label and pending batches."""
    logs = _log_rows(data_fol)
    latest = {row.lemma_id: row for row in logs}
    worklist = load_worklist(data_fol)
    listed = {item.lemma_id for item in worklist}
    return MeaningStatus(
        worklist=len(worklist),
        labelled=len(listed & latest.keys()),
        labels=dict(sorted(Counter(row.label for row in latest.values()).items())),
        pending=sorted(_pending(data_fol)),
        batches=len({row.batch for row in logs}),
    )
