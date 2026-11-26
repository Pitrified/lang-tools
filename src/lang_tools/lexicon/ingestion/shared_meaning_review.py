"""Decide whether a pt word shares its false friend's main meaning, by agent review.

A false friend's card hint carries what the look-alike mainly means
(`LookalikeHint.means`), and a drill that asks in another language can offer
those words as a trap: pt *bravo* "angry" gets *good* from it *bravo*. For a
partial false friend the pt word often means it too: it *tardi* mainly means
"late", and pt *tarde*, mostly "afternoon", is also "late". The pt word's
senses in the corpus miss uses speakers make every day, so a reviewing agent (a
Claude Code session or one of its subagents, following
``.claude/skills/shared-meaning-review/``) reads each full and partial pair,
against the rules in ``docs/guides/shared_meaning_review.md``, and says whether
Portuguese speakers use the pt word for the look-alike's main meaning.

Worklist:
    `build_worklist` lists every full and partial false-friend pair between a pt
    card and an en or it word, one item per pair, the gold pairs first, then the
    rest by the pt card's frequency; it is stored under the work folder, which is
    not committed, and rebuilt from the corpus.

Batches:
    `serve_batch` reserves the next unlabelled pairs, with the pt word's senses
    and the look-alike's main meaning. `apply_batch` validates the labels and
    records each as a `SharedMeaningRow` in
    ``data/curated/shared_meaning_log.jsonl``, the file the build applies
    (`apply_shared_meanings`) and the review's own log.

    `gold_agreement` compares the latest labels of the gold pairs with
    ``data/curated/shared_meaning_gold.jsonl``.

Label format:
    One line per item: the item number, the label, an optional ``!`` right after
    it for an edge case, and a reason after ``#``. ``s`` says the pt word is used
    for the look-alike's main meaning (the build flags the pair), ``d`` says it is
    not, ``w`` says the main meaning shown is not what the look-alike mainly
    means, and needs a reason. Blank lines and lines starting with ``#`` are
    ignored::

        1 s # chegar tarde
        2 d
        3 d! # only in Minas Gerais
        4 w # it terza is mainly "third" (fem.), not the baseball position
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
from lang_tools.lexicon.ingestion.false_friend_meaning_review import CARD_LANGUAGE
from lang_tools.lexicon.ingestion.false_friend_meaning_review import KNOWN_LANGUAGES
from lang_tools.lexicon.ingestion.false_friend_meaning_review import SenseChoice
from lang_tools.lexicon.ingestion.lookalikes import REVIEW_MODEL
from lang_tools.lexicon.ingestion.review_batches import LabelError
from lang_tools.lexicon.ingestion.review_batches import append_rows
from lang_tools.lexicon.ingestion.review_batches import guide_sha
from lang_tools.lexicon.ingestion.review_batches import locked
from lang_tools.lexicon.ingestion.review_batches import work_dir
from lang_tools.lexicon.ingestion.shared_meanings import SHARED_MEANING_LOG_FILE
from lang_tools.lexicon.ingestion.shared_meanings import SharedMeaningRow
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import read_jsonl
from lang_tools.lexicon.maintenance import write_jsonl
from lang_tools.lexicon.relations import FALSE_FRIEND_KINDS
from lang_tools.lexicon.relations import LookalikeKind

if TYPE_CHECKING:
    from collections.abc import Collection
    from collections.abc import Sequence
    from pathlib import Path

    from lang_tools.lexicon.card import LemmaCard
    from lang_tools.lexicon.lemma_store import LexiconStore

#: Every label, one per pair.
Label = Literal["s", "d", "w"]

#: The ordered worklist, under the data folder (rebuilt from the corpus).
WORKLIST_FILE = "work/shared_meaning_worklist.jsonl"
#: The hand-checked gold pairs, under ``data/curated/``.
GOLD_FILE = "shared_meaning_gold.jsonl"
#: Served, not yet applied batches live here, under the data folder (not committed).
WORK_SUBDIR = "work/shared_meaning_review"
#: Items per batch.
DEFAULT_BATCH_SIZE = 100
#: Characters of gloss and words per language shown per sense.
_GLOSS_SHOWN = 100
_WORDS_SHOWN = 5

_LABEL_RE = re.compile(r"^([sdw])(!?)$")


class UnknownRecheckWordError(LookupError):
    """Raised when a re-check names a pair the review never labelled."""

    def __init__(self, words: Sequence[str]) -> None:
        """Initialize with the words that have no label.

        Args:
            words: The unknown ``pt_text:language:known_text`` words.
        """
        self.words = list(words)
        super().__init__(f"no label to re-check for: {', '.join(self.words)}")


class SharedMeaningWorkItem(BaseModel):
    """One pair of the ordered worklist.

    Attributes:
        rank: Position in the worklist (0 is reviewed first).
        target_id: The pt word's lemma id.
        target_text: The pt word.
        known_id: The look-alike's lemma id.
        known_text: The look-alike.
        known_language: The look-alike's language.
        kind: ``full`` or ``partial``.
        sense_frequency: The pt card's frequency, which orders the worklist.
    """

    rank: int
    target_id: str
    target_text: str
    known_id: str
    known_text: str
    known_language: str
    kind: LookalikeKind
    sense_frequency: float | None = None


class SharedMeaningGold(BaseModel):
    """One hand-checked pair of the gold set (a JSONL line).

    Attributes:
        target_id: The pt word's lemma id.
        target_text: The pt word.
        known_id: The look-alike's lemma id.
        known_text: The look-alike.
        known_language: The look-alike's language.
        label: The right label.
        reason: Why, for the human reading a miss.
    """

    target_id: str
    target_text: str
    known_id: str
    known_text: str
    known_language: str
    label: Label
    reason: str = ""


class SharedMeaningBatchItem(BaseModel):
    """One item of a served batch.

    Attributes:
        n: The item's number in the batch, as the reviewer sees it.
        target_id: The pt word's lemma id.
        target_text: The pt word.
        part_of_speech: The pt word's part of speech.
        known_id: The look-alike's lemma id.
        known_text: The look-alike.
        known_language: The look-alike's language.
        kind: ``full`` or ``partial``.
        note: The edge's learner note (English).
        target_senses: Every sense of the pt word, the card's sense first.
        known_meaning: The look-alike's main meaning (its best sense), None
            when it has no sense.
    """

    n: int
    target_id: str
    target_text: str
    part_of_speech: str | None = None
    known_id: str
    known_text: str
    known_language: str
    kind: LookalikeKind
    note: str = ""
    target_senses: list[SenseChoice] = Field(default_factory=list)
    known_meaning: SenseChoice | None = None


class SharedMeaningLabel(BaseModel):
    """One parsed label line.

    Attributes:
        label: ``s``, ``d`` or ``w``.
        edge_case: The reviewer marked the item with ``!``.
        reason: Why, after ``#``.
    """

    label: Label
    edge_case: bool = False
    reason: str = ""


class GoldAgreement(BaseModel):
    """How the latest labels of the gold pairs compare with the gold set.

    Attributes:
        labelled: Gold pairs with a label.
        agree: Labels equal to the gold label.
        misses: ``"pt text ~ language text: gold -> chosen"`` for each
            disagreement.
    """

    labelled: int
    agree: int
    misses: list[str] = Field(default_factory=list)


class SharedMeaningStatus(BaseModel):
    """Progress of the review.

    Attributes:
        worklist: Pairs on the worklist.
        labelled: Worklist pairs with a label.
        labels: Label -> pairs with it (latest label per pair).
        edge_cases: Pairs whose latest label is an edge case.
        pending: Served batch ids not yet applied.
        batches: Applied batches.
    """

    worklist: int
    labelled: int
    labels: dict[str, int]
    edge_cases: int
    pending: list[str]
    batches: int


def load_gold(data_fol: Path) -> list[SharedMeaningGold]:
    """Read the gold set (empty when it does not exist)."""
    path = curated_path(data_fol, GOLD_FILE)
    return read_jsonl(SharedMeaningGold, path) if path.exists() else []


def build_worklist(
    store: LexiconStore, *, gold_pairs: Collection[tuple[str, str]] = ()
) -> list[SharedMeaningWorkItem]:
    """Return every full and partial false-friend pair of a pt card.

    The pt cards come from trap card queries in pages of `MAX_CARD_LIMIT`, every
    part of speech and inflected forms included, so every full or partial edge
    of the corpus is reached. A look-alike that is the false friend of several
    pt words is listed once per pair.

    Args:
        store: The lexicon store.
        gold_pairs: Gold ``(pt lemma id, look-alike lemma id)`` pairs, put first
            so the first batch holds them.

    Returns:
        The worklist, ranked from 0: gold pairs first, then by the pt card's
        frequency, most frequent first, then the look-alike's language and text.
    """
    taken: list[str] = []
    found: dict[tuple[str, str], SharedMeaningWorkItem] = {}
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
            for other, edge in store.get_lookalikes_for_lemma(
                card.lemma.id, languages=KNOWN_LANGUAGES, kinds=FALSE_FRIEND_KINDS
            ):
                found[card.lemma.id, other.id] = SharedMeaningWorkItem(
                    rank=0,
                    target_id=card.lemma.id,
                    target_text=card.lemma.text,
                    known_id=other.id,
                    known_text=other.text,
                    known_language=other.language,
                    kind=edge.kind,
                    sense_frequency=card.sense_frequency,
                )
    gold = set(gold_pairs)
    ordered = sorted(
        found.items(),
        key=lambda entry: (
            entry[0] not in gold,
            -(entry[1].sense_frequency or 0.0),
            entry[1].known_language,
            entry[1].known_text,
            entry[0],
        ),
    )
    return [
        item.model_copy(update={"rank": rank}) for rank, (_, item) in enumerate(ordered)
    ]


def save_worklist(data_fol: Path, items: Sequence[SharedMeaningWorkItem]) -> Path:
    """Write the worklist under the data folder; return its path."""
    return write_jsonl(items, data_fol / WORKLIST_FILE)


def load_worklist(data_fol: Path) -> list[SharedMeaningWorkItem]:
    """Read the worklist (empty when it does not exist)."""
    path = data_fol / WORKLIST_FILE
    return read_jsonl(SharedMeaningWorkItem, path) if path.exists() else []


def parse_labels(
    batch: str, text: str, numbers: Collection[int]
) -> dict[int, SharedMeaningLabel]:
    """Parse and validate a batch's label lines.

    Args:
        batch: The batch id (for the error message).
        text: The label lines (see the module docstring); blank lines and ``#``
            comments are ignored.
        numbers: The item numbers the batch was served with.

    Returns:
        Item number -> label.

    Raises:
        LabelError: Listing every unparseable line, unknown or repeated number,
            unknown label, ``w`` with no reason, and missing item.
    """
    labels: dict[int, SharedMeaningLabel] = {}
    problems: list[str] = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        n, label, problem = _parse_line(line, numbers)
        if problem:
            problems.append(problem)
        if n is None or label is None:
            continue
        if n in labels:
            problems.append(f"item {n} is labelled twice")
        labels[n] = label
    missing = sorted(set(numbers) - set(labels))
    if missing:
        problems.append(f"missing item(s) {', '.join(map(str, missing))}")
    if problems:
        raise LabelError(batch, problems)
    return labels


def _parse_line(
    line: str, numbers: Collection[int]
) -> tuple[int | None, SharedMeaningLabel | None, str]:
    """Parse one label line into its item number, label and problem, if any."""
    body, _, reason = line.partition("#")
    words = body.split()
    if not words or not words[0].isdigit():
        return None, None, f"unparseable line {line.strip()!r}"
    n = int(words[0])
    if n not in numbers:
        return None, None, f"item {n} is not in the batch"
    match = _LABEL_RE.match(words[1]) if len(words) == 2 else None  # noqa: PLR2004
    if match is None:
        return None, None, f"item {n} has no known label in {line.strip()!r}"
    label = SharedMeaningLabel(
        label=match.group(1),  # type: ignore[arg-type]
        edge_case=match.group(2) == "!",
        reason=reason.strip(),
    )
    if label.label == "w" and not label.reason:
        return n, None, f"item {n}: w needs a reason after #"
    return n, label, ""


def _log_rows(data_fol: Path) -> list[SharedMeaningRow]:
    path = curated_path(data_fol, SHARED_MEANING_LOG_FILE)
    return read_jsonl(SharedMeaningRow, path) if path.exists() else []


def _latest(
    rows: Sequence[SharedMeaningRow],
) -> dict[tuple[str, str], SharedMeaningRow]:
    """Return the latest row of each (pt lemma id, look-alike lemma id) pair."""
    return {(row.target_id, row.known_id): row for row in rows}


def _pending(data_fol: Path) -> dict[str, list[SharedMeaningBatchItem]]:
    return {
        path.stem: read_jsonl(SharedMeaningBatchItem, path)
        for path in sorted(work_dir(data_fol, WORK_SUBDIR).glob("*.jsonl"))
    }


def _choice(card: LemmaCard, languages: Sequence[str]) -> SenseChoice | None:
    """Return a card's sense as the reviewer sees it, the card's lemma left out."""
    if card.concept_id is None:
        return None
    return SenseChoice(
        concept_key=concept_key(card.concept_id),
        gloss=(card.gloss or "")[:_GLOSS_SHOWN],
        words={
            language: words[:_WORDS_SHOWN]
            for language in languages
            if (
                words := [
                    text
                    for text in card.translations.get(language, [])
                    if not (language == card.lemma.language and text == card.lemma.text)
                ]
            )
        },
    )


def _item(
    store: LexiconStore, n: int, target_id: str, known_id: str
) -> SharedMeaningBatchItem | None:
    """Return a pair as a batch item, or None when the corpus no longer has it."""
    target = store.get_lemma_by_id(target_id)
    known = store.get_lemma_by_id(known_id)
    if target is None or known is None:
        return None
    edge = next(
        (
            edge
            for other, edge in store.get_lookalikes_for_lemma(
                target_id, languages=[known.language], kinds=FALSE_FRIEND_KINDS
            )
            if other.id == known_id
        ),
        None,
    )
    if edge is None:
        return None
    languages = list(KNOWN_LANGUAGES)
    target_senses = [
        choice
        for card in store.lemma_sense_cards(target_id, translation_languages=languages)
        if (choice := _choice(card, languages)) is not None
    ]
    known_card = store.lemma_card(
        known_id, translation_languages=[CARD_LANGUAGE, *languages]
    )
    return SharedMeaningBatchItem(
        n=n,
        target_id=target.id,
        target_text=target.text,
        part_of_speech=target.part_of_speech,
        known_id=known.id,
        known_text=known.text,
        known_language=known.language,
        kind=edge.kind,
        note=edge.explanation_notes.get("en", ""),
        target_senses=target_senses,
        known_meaning=(
            _choice(known_card, [CARD_LANGUAGE, *languages]) if known_card else None
        ),
    )


def serve_batch(
    data_fol: Path,
    store: LexiconStore,
    *,
    batch: str,
    size: int = DEFAULT_BATCH_SIZE,
) -> list[SharedMeaningBatchItem]:
    """Reserve the next unlabelled worklist pairs as a batch.

    The batch is written under the work folder, so concurrent reviewers never
    get the same pairs, and `apply_batch` can check the labels against the items
    it showed. Serving an id that is already pending returns that batch
    unchanged. A worklist pair the corpus no longer has is skipped.

    Args:
        data_fol: Project data folder.
        store: The lexicon store, for the senses.
        batch: The batch id (e.g. ``p0001``).
        size: Pairs to reserve.

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
        taken = {(row.target_id, row.known_id) for row in logs} | {
            (item.target_id, item.known_id)
            for items in pending.values()
            for item in items
        }
        items: list[SharedMeaningBatchItem] = []
        for work in load_worklist(data_fol):
            if len(items) == size:
                break
            if (work.target_id, work.known_id) in taken:
                continue
            item = _item(store, len(items) + 1, work.target_id, work.known_id)
            if item is not None:
                items.append(item)
        if items:
            append_rows(work_dir(data_fol, WORK_SUBDIR) / f"{batch}.jsonl", items)
            lg.info("Served batch {}: {} pair(s)", batch, len(items))
        return items


def recheck_batch(
    data_fol: Path,
    store: LexiconStore,
    *,
    batch: str,
    words: Sequence[str],
) -> list[SharedMeaningBatchItem]:
    """Serve already labelled pairs again, to be labelled anew.

    The batch skips the reservations: its pairs have a label already, and the
    new one wins when applied. Serving an id that is already pending returns
    that batch unchanged.

    Args:
        data_fol: Project data folder.
        store: The lexicon store, for the senses.
        batch: The batch id (e.g. ``p9001``).
        words: The pairs as ``pt_text:language:known_text`` (``tarde:it:tardi``).
            A word names every labelled pair with those texts (a pt word with
            two parts of speech is two lemmas).

    Returns:
        The batch items, in the order of ``words``.

    Raises:
        UnknownRecheckWordError: When a word has no label in the review log, or
            the corpus no longer has its pair.
    """
    with locked(data_fol, WORK_SUBDIR):
        path = work_dir(data_fol, WORK_SUBDIR) / f"{batch}.jsonl"
        if path.exists():
            return read_jsonl(SharedMeaningBatchItem, path)
        by_word: dict[str, list[tuple[str, str]]] = {}
        for pair, row in _latest(_log_rows(data_fol)).items():
            word = f"{row.target_text}:{row.known_language}:{row.known_text}"
            by_word.setdefault(word, []).append(pair)
        missing = [word for word in words if word not in by_word]
        if missing:
            raise UnknownRecheckWordError(missing)
        items: list[SharedMeaningBatchItem] = []
        gone: list[str] = []
        for word in words:
            for target_id, known_id in by_word[word]:
                item = _item(store, len(items) + 1, target_id, known_id)
                if item is None:
                    gone.append(word)
                else:
                    items.append(item)
        if gone:
            raise UnknownRecheckWordError(gone)
        append_rows(path, items)
        lg.info("Served re-check {}: {} pair(s)", batch, len(items))
        return items


def _words_line(sense: SenseChoice) -> str:
    """Return a sense as ``gloss [language: words | ...]``."""
    words = " | ".join(
        f"{language}: {', '.join(texts)}" for language, texts in sense.words.items()
    )
    return f"{sense.gloss} [{words}]"


def render_batch(items: Sequence[SharedMeaningBatchItem]) -> str:
    """Return the batch as the lines a reviewer reads."""
    lines: list[str] = []
    for item in items:
        pos = f" ({item.part_of_speech})" if item.part_of_speech else ""
        lines.append(
            f"{item.n} {CARD_LANGUAGE} {item.target_text}{pos}"
            f" ~ {item.known_language} {item.known_text} ({item.kind})"
        )
        lines.append(f"  note: {item.note}")
        label = f"  {CARD_LANGUAGE} senses: "
        if not item.target_senses:
            lines.append(f"{label}(no sense)")
        for k, sense in enumerate(item.target_senses, start=1):
            lead = label if k == 1 else " " * len(label)
            lines.append(f"{lead}{k} {_words_line(sense)}")
        meaning = (
            _words_line(item.known_meaning) if item.known_meaning else "(no sense)"
        )
        lines.append(
            f"  {item.known_language} {item.known_text} mainly means: {meaning}"
        )
    return "\n".join(lines)


def apply_batch(
    data_fol: Path, batch: str, labels_text: str, *, guide_path: Path
) -> list[SharedMeaningRow]:
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
        items = read_jsonl(SharedMeaningBatchItem, path)
        labels = parse_labels(batch, labels_text, {item.n for item in items})
        sha = guide_sha(guide_path)
        log = [
            SharedMeaningRow(
                batch=batch,
                target_id=item.target_id,
                target_text=item.target_text,
                known_id=item.known_id,
                known_text=item.known_text,
                known_language=item.known_language,
                kind=item.kind,
                label=labels[item.n].label,
                edge_case=labels[item.n].edge_case,
                reason=labels[item.n].reason,
                model=REVIEW_MODEL,
                rulebook_sha=sha,
            )
            for item in items
        ]
        append_rows(curated_path(data_fol, SHARED_MEANING_LOG_FILE), log)
        path.unlink()
        counts = Counter(row.label for row in log)
        lg.info(
            "Applied batch {}: {} pair(s) {}",
            batch,
            len(log),
            dict(sorted(counts.items())),
        )
        return log


def gold_agreement(data_fol: Path) -> GoldAgreement:
    """Compare the latest label of each labelled gold pair with the gold set."""
    latest = _latest(_log_rows(data_fol))
    agree = 0
    misses: list[str] = []
    labelled = 0
    for gold in load_gold(data_fol):
        row = latest.get((gold.target_id, gold.known_id))
        if row is None:
            continue
        labelled += 1
        if row.label == gold.label:
            agree += 1
        else:
            misses.append(
                f"{CARD_LANGUAGE} {gold.target_text} ~ {gold.known_language}"
                f" {gold.known_text}: {gold.label} -> {row.label}"
            )
    return GoldAgreement(labelled=labelled, agree=agree, misses=misses)


def review_status(data_fol: Path) -> SharedMeaningStatus:
    """Return how far the review has come: counts per label and pending batches."""
    logs = _log_rows(data_fol)
    latest = _latest(logs)
    worklist = load_worklist(data_fol)
    listed = {(item.target_id, item.known_id) for item in worklist}
    return SharedMeaningStatus(
        worklist=len(worklist),
        labelled=len(listed & latest.keys()),
        labels=dict(sorted(Counter(row.label for row in latest.values()).items())),
        edge_cases=sum(row.edge_case for row in latest.values()),
        pending=sorted(_pending(data_fol)),
        batches=len({row.batch for row in logs}),
    )
