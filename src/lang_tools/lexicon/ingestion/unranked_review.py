"""Sort the pt words that have no frequency, in batches, through the agent harness.

wordfreq has never seen about five thousand single-word pt lemmas. Some are real
words a learner meets (*peúga*), some are real but rare (*conquiliologia*), and the
rest are not words a drill should teach: a misspelling (*magestoso*), a word of
another language (*walkout*), a glued or broken form (*canodachaminé*). A
reviewing agent (a Claude Code session or one of its subagents, following
``.claude/skills/unranked-review/``) labels each word against the rules in
``docs/guides/unranked_review.md``.

Worklist:
    `build_worklist` lists the single lowercase pt lemmas with no token frequency
    on any sense, by lemma id; it is stored under the work folder, which is not
    committed, and rebuilt from the corpus.

Batches:
    `serve_batch` reserves the next unlabelled words, with the concepts each is
    linked to. `apply_batch` validates the labels and records them:

    - every label gets an `UnrankedLogRow` in
      ``data/curated/unranked_review_log.jsonl``;
    - a misspelled, foreign or malformed word (``m``, ``f``, ``x``) gets one
      `FormDrop` row (kind `DROP_KIND`) per concept link in
      ``data/curated/member_form_drops.jsonl``, so the build removes the lemma;
    - a real word (``c``, ``u``, ``r``) gets a `CommonnessBucket` row in
      ``data/curated/commonness_buckets.jsonl``; `load_buckets` returns the
      latest row per lemma, for the score that stands in for the missing
      frequency.

Label format:
    One line per item: the item number, the label, an extra where the label
    takes one, and a reason after ``#``. ``m`` takes the correct spelling, ``f``
    the language code of the word; ``m``, ``f`` and ``x`` need a reason, ``c``,
    ``u`` and ``r`` take none (a comment is kept). Blank lines and lines
    starting with ``#`` are ignored::

        1 c
        2 u
        3 r # a mineral
        4 m majestoso # missing j
        5 f en # English loanword, pt says "saída"
        6 x # two words glued together
"""

from __future__ import annotations

from collections import Counter
import re
from typing import TYPE_CHECKING
from typing import Literal

from loguru import logger as lg
from pydantic import BaseModel
from pydantic import Field

from lang_tools.lexicon.concept_id import concept_key
from lang_tools.lexicon.ingestion.form_review import MEMBER_FORM_DROPS_FILE
from lang_tools.lexicon.ingestion.form_review import FormDrop
from lang_tools.lexicon.ingestion.lookalikes import REVIEW_MODEL
from lang_tools.lexicon.ingestion.review_batches import LabelError
from lang_tools.lexicon.ingestion.review_batches import append_rows
from lang_tools.lexicon.ingestion.review_batches import guide_sha
from lang_tools.lexicon.ingestion.review_batches import locked
from lang_tools.lexicon.ingestion.review_batches import work_dir
from lang_tools.lexicon.maintenance import ReviewStatus
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import read_jsonl
from lang_tools.lexicon.maintenance import write_jsonl

if TYPE_CHECKING:
    from collections.abc import Collection
    from collections.abc import Sequence
    from pathlib import Path

    from lang_tools.lexicon.lemma_store import LexiconStore

#: Every label, one per word.
Label = Literal["c", "u", "r", "m", "f", "x"]
#: Labels that put a word in a commonness bucket, and the bucket names.
BUCKET_NAMES: dict[str, str] = {"c": "common", "u": "uncommon", "r": "rare"}
#: Labels that drop the word, and what each means (the drop reason's prefix).
DROP_NAMES: dict[str, str] = {
    "m": "misspelled",
    "f": "not Portuguese",
    "x": "malformed",
}

#: The ordered worklist, under the data folder (rebuilt from the corpus).
WORKLIST_FILE = "work/unranked_review_worklist.jsonl"
#: One row per labelled word, under ``data/curated/``.
REVIEW_LOG_FILE = "unranked_review_log.jsonl"
#: The commonness buckets of the real words, under ``data/curated/``.
BUCKETS_FILE = "commonness_buckets.jsonl"
#: Served, not yet applied batches live here, under the data folder (not committed).
WORK_SUBDIR = "work/unranked_review"
#: Items per batch.
DEFAULT_BATCH_SIZE = 200
#: The `FormDrop.kind` of a word this review drops.
DROP_KIND = "unranked"
#: The language the worklist covers.
LANGUAGE = "pt"
#: Characters of gloss and English members shown per concept link.
_GLOSS_SHOWN = 120
_MEMBERS_SHOWN = 6

_LABELS = frozenset({"c", "u", "r", "m", "f", "x"})
_LANGUAGE_CODE_RE = re.compile(r"^[a-z]{2,3}$")


class UnrankedWorkItem(BaseModel):
    """One word of the ordered worklist.

    Attributes:
        rank: Position in the worklist (0 is reviewed first).
        lemma_id: The lemma.
        lemma_text: Its form.
        language: Its language.
    """

    rank: int
    lemma_id: str
    lemma_text: str
    language: str = LANGUAGE


class ConceptLink(BaseModel):
    """One concept a served word is linked to, as the reviewer sees it.

    Attributes:
        concept_key: The concept (`concept_key`).
        gloss: The concept's English gloss.
        members: Up to a few of its English members.
    """

    concept_key: str
    gloss: str = ""
    members: list[str] = Field(default_factory=list)


class UnrankedBatchItem(BaseModel):
    """One item of a served batch.

    Attributes:
        n: The item's number in the batch, as the reviewer sees it.
        lemma_id: The lemma.
        lemma_text: Its form.
        language: Its language.
        part_of_speech: The lemma's part of speech.
        links: Every concept the lemma is linked to.
    """

    n: int
    lemma_id: str
    lemma_text: str
    language: str = LANGUAGE
    part_of_speech: str | None = None
    links: list[ConceptLink] = Field(default_factory=list)


class UnrankedLabel(BaseModel):
    """One parsed label line.

    Attributes:
        label: The label letter.
        extra: The correct spelling (``m``) or the language code (``f``).
        reason: Why, after ``#``.
    """

    label: Label
    extra: str = ""
    reason: str = ""


class UnrankedLogRow(BaseModel):
    """One labelled word (a line of the review log).

    Attributes:
        batch: The batch id.
        lemma_id: The lemma.
        language: Its language.
        text: Its form.
        label: The label letter.
        extra: The correct spelling (``m``) or the language code (``f``).
        reason: The reviewer's reason.
        rulebook_sha: Hash of the rulebook the batch was labelled against.
    """

    batch: str
    lemma_id: str
    language: str
    text: str
    label: Label
    extra: str = ""
    reason: str = ""
    rulebook_sha: str = ""


class CommonnessBucket(BaseModel):
    """The commonness of a real word with no frequency (a JSONL line).

    Attributes:
        lemma_id: The lemma.
        language: Its language.
        text: Its form (review aid).
        bucket: ``common``, ``uncommon`` or ``rare``.
        rulebook_sha: Hash of the rulebook the row was labelled against.
        status: ``accepted`` once the row counts.
        batch: The review batch that wrote the row.
    """

    lemma_id: str
    language: str
    text: str
    bucket: Literal["common", "uncommon", "rare"]
    rulebook_sha: str = ""
    status: ReviewStatus = "proposed"
    batch: str = ""


class UnrankedStatus(BaseModel):
    """Progress of the review.

    Attributes:
        worklist: Words on the worklist.
        labelled: Worklist words with a label.
        labels: Label letter -> words with it (latest label per word).
        pending: Served batch ids not yet applied.
        batches: Applied batches.
    """

    worklist: int
    labelled: int
    labels: dict[str, int]
    pending: list[str]
    batches: int


def build_worklist(store: LexiconStore) -> list[UnrankedWorkItem]:
    """Return the single lowercase pt words with no token frequency, by lemma id.

    A word qualifies when it is one lowercase alphabetic token (accented
    letters count) and none of its senses has a token frequency.

    Args:
        store: The lexicon store.

    Returns:
        The worklist, ranked from 0. Lemma ids are hashes, so their order mixes
        the alphabet and the first batches are a fair sample of the whole.
    """
    found = sorted(
        (
            lemma
            for lemma in store.get_lemmas_by_language(LANGUAGE)
            if lemma.text.isalpha()
            and lemma.text == lemma.text.lower()
            and all(
                sense.token_frequency is None
                for sense in store.senses_for_lemma(lemma.id)
            )
        ),
        key=lambda lemma: lemma.id,
    )
    return [
        UnrankedWorkItem(rank=rank, lemma_id=lemma.id, lemma_text=lemma.text)
        for rank, lemma in enumerate(found)
    ]


def save_worklist(data_fol: Path, items: Sequence[UnrankedWorkItem]) -> Path:
    """Write the worklist under the data folder; return its path."""
    return write_jsonl(items, data_fol / WORKLIST_FILE)


def load_worklist(data_fol: Path) -> list[UnrankedWorkItem]:
    """Read the worklist (empty when it does not exist)."""
    path = data_fol / WORKLIST_FILE
    return read_jsonl(UnrankedWorkItem, path) if path.exists() else []


def load_buckets(data_fol: Path) -> dict[str, CommonnessBucket]:
    """Return the accepted bucket of each lemma, the latest row per lemma.

    Args:
        data_fol: Project data folder.

    Returns:
        Lemma id -> its bucket row (empty when the file does not exist).
    """
    path = curated_path(data_fol, BUCKETS_FILE)
    if not path.exists():
        return {}
    latest: dict[str, CommonnessBucket] = {}
    for row in read_jsonl(CommonnessBucket, path):
        latest.pop(row.lemma_id, None)
        latest[row.lemma_id] = row
    return {lid: row for lid, row in latest.items() if row.status == "accepted"}


def parse_labels(
    batch: str, text: str, item_numbers: Collection[int]
) -> dict[int, UnrankedLabel]:
    """Parse and validate a batch's label lines.

    Args:
        batch: The batch id (for the error message).
        text: The label lines (see the module docstring); blank lines and ``#``
            comments are ignored.
        item_numbers: The numbers of the served items.

    Returns:
        Item number -> label.

    Raises:
        LabelError: Listing every unparseable line, unknown or repeated number,
            unknown label, missing spelling, language code or reason, extra
            where the label takes none, and missing item.
    """
    labels: dict[int, UnrankedLabel] = {}
    problems: list[str] = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        n, label, line_problems = _parse_line(line, item_numbers)
        problems += line_problems
        if n is None or label is None:
            continue
        if n in labels:
            problems.append(f"item {n} is labelled twice")
        labels[n] = label
    missing = sorted(set(item_numbers) - set(labels))
    if missing:
        problems.append(f"missing item(s) {', '.join(map(str, missing))}")
    if problems:
        raise LabelError(batch, problems)
    return labels


def _parse_line(
    line: str, item_numbers: Collection[int]
) -> tuple[int | None, UnrankedLabel | None, list[str]]:
    """Parse one label line into its item number, label and problems."""
    body, _, reason = line.partition("#")
    words = body.split()
    reason = reason.strip()
    if not words or not words[0].isdigit():
        return None, None, [f"unparseable line {line.strip()!r}"]
    n = int(words[0])
    if n not in item_numbers:
        return None, None, [f"item {n} is not in the batch"]
    if len(words) < 2 or words[1] not in _LABELS:  # noqa: PLR2004
        return None, None, [f"item {n} has no known label in {line.strip()!r}"]
    letter = words[1]
    extras = words[2:]
    problems = _label_problems(n, letter, extras, reason)
    label = UnrankedLabel(
        label=letter,  # type: ignore[arg-type]
        extra=extras[0] if extras else "",
        reason=reason,
    )
    return n, label, problems


def _label_problems(
    n: int, letter: str, extras: Sequence[str], reason: str
) -> list[str]:
    """Return what is wrong with one parsed label (empty when it is valid)."""
    problems: list[str] = []
    if letter == "m":
        if len(extras) != 1:
            problems.append(f"item {n}: m needs the correct spelling, one word")
        elif not extras[0].isalpha() or extras[0] != extras[0].lower():
            problems.append(f"item {n}: {extras[0]!r} is not a lowercase word")
    elif letter == "f":
        if len(extras) != 1 or not _LANGUAGE_CODE_RE.match(extras[0]):
            problems.append(f"item {n}: f needs a language code (en, it, ...)")
    elif extras:
        problems.append(f"item {n}: {letter} takes nothing before the reason")
    if letter in DROP_NAMES and not reason:
        problems.append(f"item {n}: {letter} needs a reason after #")
    return problems


def _reviewed_ids(data_fol: Path) -> set[str]:
    return {row.lemma_id for row in _log_rows(data_fol)}


def _log_rows(data_fol: Path) -> list[UnrankedLogRow]:
    path = curated_path(data_fol, REVIEW_LOG_FILE)
    return read_jsonl(UnrankedLogRow, path) if path.exists() else []


def _pending(data_fol: Path) -> dict[str, list[UnrankedBatchItem]]:
    return {
        path.stem: read_jsonl(UnrankedBatchItem, path)
        for path in sorted(work_dir(data_fol, WORK_SUBDIR).glob("u*.jsonl"))
    }


def _links(store: LexiconStore, lemma_id_: str) -> list[ConceptLink]:
    """Return the concepts a lemma is linked to, with English members."""
    links = []
    for concept in store.concepts_for_lemma(lemma_id_):
        members = store.lemmas_for_concept(concept.id, "en")
        links.append(
            ConceptLink(
                concept_key=concept_key(concept.id),
                gloss=concept.definitions.get("en", "")[:_GLOSS_SHOWN],
                members=[m.text for m in members][:_MEMBERS_SHOWN],
            )
        )
    return links


def serve_batch(
    data_fol: Path,
    store: LexiconStore,
    *,
    batch: str,
    size: int = DEFAULT_BATCH_SIZE,
) -> list[UnrankedBatchItem]:
    """Reserve the next unlabelled worklist words as a batch.

    The batch is written under the work folder, so concurrent reviewers never
    get the same words, and `apply_batch` can check the labels against the items
    it showed. Serving an id that is already pending returns that batch
    unchanged.

    Args:
        data_fol: Project data folder.
        store: The lexicon store, for the concepts.
        batch: The batch id (e.g. ``u0001``).
        size: Words to reserve.

    Returns:
        The batch items (empty when the worklist is done).

    Raises:
        ValueError: When the batch id was already applied.
    """
    with locked(data_fol, WORK_SUBDIR):
        pending = _pending(data_fol)
        if batch in pending:
            return pending[batch]
        if any(row.batch == batch for row in _log_rows(data_fol)):
            msg = f"batch {batch} was already applied"
            raise ValueError(msg)
        taken = _reviewed_ids(data_fol) | {
            item.lemma_id for items in pending.values() for item in items
        }
        todo = [item for item in load_worklist(data_fol) if item.lemma_id not in taken]
        picked = todo[:size]
        items = []
        for n, work in enumerate(picked, start=1):
            lemma = store.get_lemma_by_id(work.lemma_id)
            items.append(
                UnrankedBatchItem(
                    n=n,
                    lemma_id=work.lemma_id,
                    lemma_text=work.lemma_text,
                    part_of_speech=lemma.part_of_speech if lemma else None,
                    links=_links(store, work.lemma_id),
                )
            )
        if items:
            append_rows(work_dir(data_fol, WORK_SUBDIR) / f"{batch}.jsonl", items)
            lg.info("Served batch {}: {} word(s)", batch, len(items))
        return items


def render_batch(items: Sequence[UnrankedBatchItem]) -> str:
    """Return the batch as the lines a reviewer reads."""
    lines: list[str] = []
    for item in items:
        pos = f" ({item.part_of_speech})" if item.part_of_speech else ""
        lines.append(f"{item.n} {item.lemma_text}{pos}")
        lines += [f"  {link.gloss} [{', '.join(link.members)}]" for link in item.links]
    return "\n".join(lines)


def apply_batch(
    data_fol: Path, batch: str, labels_text: str, *, guide_path: Path
) -> list[UnrankedLogRow]:
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
        items = read_jsonl(UnrankedBatchItem, path)
        labels = parse_labels(batch, labels_text, [item.n for item in items])
        sha = guide_sha(guide_path)
        log: list[UnrankedLogRow] = []
        drops: list[FormDrop] = []
        buckets: list[CommonnessBucket] = []
        for item in items:
            label = labels[item.n]
            log.append(
                UnrankedLogRow(
                    batch=batch,
                    lemma_id=item.lemma_id,
                    language=item.language,
                    text=item.lemma_text,
                    label=label.label,
                    extra=label.extra,
                    reason=label.reason,
                    rulebook_sha=sha,
                )
            )
            if label.label in DROP_NAMES:
                drops += _drop_rows(item, label, sha=sha, batch=batch)
            else:
                buckets.append(
                    CommonnessBucket(
                        lemma_id=item.lemma_id,
                        language=item.language,
                        text=item.lemma_text,
                        bucket=BUCKET_NAMES[label.label],  # type: ignore[arg-type]
                        rulebook_sha=sha,
                        status="accepted",
                        batch=batch,
                    )
                )
        append_rows(curated_path(data_fol, MEMBER_FORM_DROPS_FILE), drops)
        append_rows(curated_path(data_fol, BUCKETS_FILE), buckets)
        append_rows(curated_path(data_fol, REVIEW_LOG_FILE), log)
        path.unlink()
        counts = Counter(row.label for row in log)
        lg.info(
            "Applied batch {}: {} word(s) {}, {} drop row(s)",
            batch,
            len(log),
            dict(sorted(counts.items())),
            len(drops),
        )
        return log


def _drop_rows(
    item: UnrankedBatchItem, label: UnrankedLabel, *, sha: str, batch: str
) -> list[FormDrop]:
    """Return one drop row per concept link of a word the review drops."""
    detail = {"m": "correct spelling", "f": "language"}.get(label.label)
    note = f"{DROP_NAMES[label.label]}"
    if detail and label.extra:
        note += f" ({detail} {label.extra})"
    reason = f"{note}: {label.reason}"
    return [
        FormDrop(
            lemma_id=item.lemma_id,
            concept_key=link.concept_key,
            language=item.language,
            form=item.lemma_text,
            kind=DROP_KIND,
            drop=True,
            reason=reason,
            status="accepted",
            model=REVIEW_MODEL,
            prompt_sha=sha,
            batch=batch,
        )
        for link in item.links
    ]


def review_status(data_fol: Path) -> UnrankedStatus:
    """Return how far the review has come: counts per label and pending batches."""
    latest = {row.lemma_id: row for row in _log_rows(data_fol)}
    worklist = load_worklist(data_fol)
    listed = {item.lemma_id for item in worklist}
    return UnrankedStatus(
        worklist=len(worklist),
        labelled=len(listed & latest.keys()),
        labels=dict(sorted(Counter(row.label for row in latest.values()).items())),
        pending=sorted(_pending(data_fol)),
        batches=len({row.batch for row in _log_rows(data_fol)}),
    )
