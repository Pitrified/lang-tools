"""Review the most frequent drill cards in batches through the agent harness.

A card shows its lemma's best sense, and for the most frequent words that pick
is often wrong in one of two ways a rule cannot see: the lemma is linked to a
concept it never means (pt *seja* "are", the unit: a form of *ser*), or the
right sense exists and loses the pick (pt *tarde* "night"). A reviewing agent
(a Claude Code session or one of its subagents, following
``.claude/skills/sense-review/``) reads each card with all its senses, against
the rules in ``docs/guides/sense_review.md``, and keeps the card, pins another
sense, drops the wrong links, or adds the meaning the corpus does not link (pt
*sim* has only "yea").

Worklist:
    `build_worklist` takes the most frequent single-word cards of a language,
    in the cards' own frequency order, leaving the gold lemmas out;
    `removed_lemmas` lists the lemmas a review removed, which are served with
    the links it dropped.

Batches:
    `serve_batch` reserves the next unreviewed lemmas and mixes in a few hidden
    gold lemmas. `apply_batch` validates the labels and records them as curated
    inputs the build re-applies:

    - every reviewed lemma gets a `BestSense` row in
      ``data/curated/best_senses.jsonl`` (the pinned sense, or no concept to
      keep the frequency pick), which also marks the lemma as reviewed;
    - every dropped sense gets a `FormDrop` row (kind `DROP_KIND`) in
      ``data/curated/member_form_drops.jsonl``; a lemma left without a sense
      leaves the corpus;
    - every added link gets a `SenseAddition` row in
      ``data/curated/sense_additions.jsonl``, and its `BestSense` row pins it.

    The batch's numbers, and each item's `SenseOutcome`, go to
    ``data/curated/sense_review_log.jsonl``. `recheck_batch` serves reviewed
    lemmas again under a new rulebook; with ``shadow`` it serves a second,
    blind review whose outcomes go to ``sense_review_shadow_log.jsonl`` only,
    and `agreement` compares the two.

Corrections:
    A wrong verdict is corrected by hand, outside the batches: `restore_drops`
    writes a later ``drop: false`` row that retracts a drop, `pin_sense` a
    later `BestSense` row, `drop_sense` a drop met outside a batch, and
    `add_sense` a sense addition with its pin; in every file the latest row
    wins.

Label format:
    One line per item. Senses are numbered in the card's pick order, so sense 1
    is the current card. ``k`` keeps it; ``pK`` pins sense K; ``dK,L`` drops
    senses K and L (the card falls to the best sense left); ``x`` drops every
    link; ``aKEY`` adds a link to concept ``KEY`` and pins it, with an optional
    form note in braces. ``p``, ``d`` and ``a`` combine, but not ``p`` with
    ``a``; ``k`` and ``x`` stand alone; a removed lemma takes ``k`` or ``a``. A
    drop or an addition needs a reason after the actions. A ``!`` right after
    an action marks an edge case::

        1 k
        2 p3
        3 d1 a form of ser; "are" is the unit
        4 p2 d1! pt "tarde" is never the night
        5 x a form of ter; "ringworm" is a rare homograph
        6 d1 a0123456789ab "yes" is the everyday meaning; "yea" is rare
        7 a0123456789ab {3rd person plural present of "ser": they are} the verb
"""

from __future__ import annotations

from collections import Counter
import random
import re
from typing import TYPE_CHECKING

from loguru import logger as lg
from pydantic import BaseModel
from pydantic import Field

from lang_tools.lexicon.card import MAX_CARD_LIMIT
from lang_tools.lexicon.card import CardQuery
from lang_tools.lexicon.concept_id import concept_key
from lang_tools.lexicon.ingestion.best_senses import BEST_SENSES_FILE
from lang_tools.lexicon.ingestion.best_senses import BestSense
from lang_tools.lexicon.ingestion.closed_class import CLOSED_CLASS
from lang_tools.lexicon.ingestion.form_review import MEMBER_FORM_DROPS_FILE
from lang_tools.lexicon.ingestion.form_review import FormDrop
from lang_tools.lexicon.ingestion.form_review import load_form_drops
from lang_tools.lexicon.ingestion.lookalikes import REVIEW_MODEL
from lang_tools.lexicon.ingestion.review_batches import LabelError
from lang_tools.lexicon.ingestion.review_batches import append_rows
from lang_tools.lexicon.ingestion.review_batches import guide_sha
from lang_tools.lexicon.ingestion.review_batches import locked
from lang_tools.lexicon.ingestion.review_batches import work_dir
from lang_tools.lexicon.ingestion.sense_additions import SENSE_ADDITIONS_FILE
from lang_tools.lexicon.ingestion.sense_additions import SenseAddition
from lang_tools.lexicon.lemma_id import lemma_id
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import read_jsonl

if TYPE_CHECKING:
    from collections.abc import Collection
    from collections.abc import Mapping
    from collections.abc import Sequence
    from pathlib import Path

    from lang_tools.lexicon.lemma_store import LexiconStore

#: The committed, ordered worklist, under ``data/curated/``.
WORKLIST_FILE = "sense_worklist.jsonl"
#: The hand-checked gold lemmas, under ``data/curated/``.
GOLD_FILE = "sense_review_gold.jsonl"
#: One row per applied batch, under ``data/curated/``.
REVIEW_LOG_FILE = "sense_review_log.jsonl"
#: One row per applied second-review batch, under ``data/curated/``.
SHADOW_LOG_FILE = "sense_review_shadow_log.jsonl"
#: Served, not yet applied batches live here, under the data folder (not committed).
WORK_SUBDIR = "work/sense_review"
#: Served second-review batches, apart from the batches that write rows.
SHADOW_SUBDIR = "work/sense_review/shadow"
#: Cards per worklist, items per batch, and hidden gold lemmas mixed into each.
DEFAULT_WORKLIST_SIZE = 1000
DEFAULT_BATCH_SIZE = 200
DEFAULT_GOLD_PER_BATCH = 2
#: The `FormDrop.kind` of a reviewed wrong link.
DROP_KIND = "wrong link"
#: Reviewer tag and batch of the rows a hand correction writes.
CORRECTION_MODEL = "manual"
CORRECTION_BATCH = "correction"
#: Characters of gloss and translations shown per sense.
_GLOSS_SHOWN = 80
_TRANSLATIONS_SHOWN = 4

_ACTION_RE = re.compile(r"^(k|x|p\d+|d\d+(?:,\d+)*|a[0-9a-f]{12})(!?)$")
_FORM_NOTE_RE = re.compile(r"\{([^}]*)\}")


class CorrectionError(ValueError):
    """A hand correction names a sense or a drop the data does not have."""

    def __init__(self, language: str, word: str, problem: str) -> None:
        """Name the lemma and what is missing."""
        super().__init__(f"{language} {word!r}: {problem}")


class SenseWorkItem(BaseModel):
    """One card of the ordered worklist.

    Attributes:
        rank: Position in the worklist (0 is reviewed first).
        lemma_id: The card's lemma.
        lemma_text: Its form.
        language: Its language.
        sense_frequency: The card's frequency, which orders the worklist.
    """

    rank: int
    lemma_id: str
    lemma_text: str
    language: str
    sense_frequency: float | None = None


class SenseGold(BaseModel):
    """One hand-checked lemma of the gold set (a JSONL line).

    Attributes:
        lemma_id: The lemma.
        lemma_text: Its form.
        language: Its language.
        best: The concept keys a right card may show; empty when every link of
            the lemma is wrong.
        reason: Why, for the human reading a miss.
    """

    lemma_id: str
    lemma_text: str
    language: str
    best: list[str] = Field(default_factory=list)
    reason: str = ""


class SenseOption(BaseModel):
    """One sense of a served item, as the reviewer sees it.

    Attributes:
        concept_key: The sense's concept (`concept_key`).
        gloss: The concept's English gloss.
        translations: Its top English translations.
    """

    concept_key: str
    gloss: str = ""
    translations: list[str] = Field(default_factory=list)


class SenseBatchItem(BaseModel):
    """One item of a served batch.

    Attributes:
        n: The item's number in the batch, as the reviewer sees it.
        lemma_id: The lemma.
        lemma_text: Its form.
        language: Its language.
        part_of_speech: The lemma's part of speech.
        senses: Every sense, in the card's pick order (sense 1 is the card).
        rank: Worklist rank, or None for a hidden gold item.
        gold_best: The gold concept keys of a hidden gold item; None for a
            worklist item.
        removed: The lemma is not in the corpus (the review dropped every
            link); `senses` are the dropped links.
    """

    n: int
    lemma_id: str
    lemma_text: str
    language: str
    part_of_speech: str | None = None
    senses: list[SenseOption] = Field(default_factory=list)
    rank: int | None = None
    gold_best: list[str] | None = None
    removed: bool = False


class SenseLabel(BaseModel):
    """One parsed label line.

    Attributes:
        pin: The pinned sense number, if any.
        drops: The dropped sense numbers.
        drop_all: Every link is wrong.
        add: The concept key of a link to add, which the card then shows.
        form_note: Which form of the word the added sense is (``{...}``).
        reason: Why the senses are dropped or added.
        edge_case: Flagged with ``!``.
    """

    pin: int | None = None
    drops: list[int] = Field(default_factory=list)
    drop_all: bool = False
    add: str | None = None
    form_note: str = ""
    reason: str = ""
    edge_case: bool = False

    def card(self, senses: Sequence[SenseOption]) -> str | None:
        """Return the concept key the card shows after the label (None: no card)."""
        if self.add is not None:
            return self.add
        if self.drop_all:
            return None
        if self.pin is not None:
            return senses[self.pin - 1].concept_key
        left = [s for i, s in enumerate(senses, 1) if i not in self.drops]
        return left[0].concept_key if left else None


class SenseOutcome(BaseModel):
    """What one label does to one item, for comparing two reviews of it.

    Attributes:
        lemma_text: The item's lemma (review aid).
        kept: The label was ``k``.
        card: The concept key the card shows after the label (None: no card).
        drops: The dropped concept keys.
        add: The added concept key, if any.
    """

    lemma_text: str
    kept: bool
    card: str | None = None
    drops: list[str] = Field(default_factory=list)
    add: str | None = None


class SenseReviewLogRow(BaseModel):
    """The numbers of one applied batch (a line of the review log).

    Attributes:
        batch: The batch id.
        language: The batch's language.
        items: Worklist items labelled.
        kept: Items whose card was right.
        pinned: Items with a pinned sense.
        dropped_senses: Senses dropped, over all items.
        dropped_lemmas: Items with every link dropped.
        added: Items with an added link.
        edge_cases: Worklist items flagged as edge cases.
        gold_keys: The hidden gold lemmas' ids.
        gold_agree: Hidden gold items whose card the reviewer got right.
        gold_misses: ``"lemma: gold -> card"`` for each disagreement.
        guide_sha: Hash of the review guide the batch was labelled against.
        outcomes: Lemma id -> what the label did, per worklist item.
    """

    batch: str
    language: str
    items: int
    kept: int = 0
    pinned: int = 0
    dropped_senses: int = 0
    dropped_lemmas: int = 0
    added: int = 0
    edge_cases: int = 0
    gold_keys: list[str] = Field(default_factory=list)
    gold_agree: int = 0
    gold_misses: list[str] = Field(default_factory=list)
    guide_sha: str = ""
    outcomes: dict[str, SenseOutcome] = Field(default_factory=dict)


class SenseAgreement(BaseModel):
    """How two reviews of the same items compare (`agreement`).

    Attributes:
        items: Worklist items both reviews labelled.
        same_card: Items whose card is the same after both labels.
        same_outcome: Items with the same card, drops and addition.
        first_changed: Items the first review did not keep.
        agree_on_changed: Of those, items with the same outcome in both.
        disagreements: ``"lemma: first -> second"`` per differing outcome.
    """

    items: int
    same_card: int
    same_outcome: int
    first_changed: int
    agree_on_changed: int
    disagreements: list[str] = Field(default_factory=list)


class SenseReviewStatus(BaseModel):
    """Progress of the review.

    Attributes:
        languages: Language -> ``(reviewed, total)`` worklist items.
        pending: Served batch ids not yet applied.
        batches: Applied batches.
        gold_agree: Hidden gold items labelled right, over all batches.
        gold_total: Hidden gold items served in applied batches.
        edge_cases: Worklist items flagged as edge cases.
    """

    languages: dict[str, tuple[int, int]]
    pending: list[str]
    batches: int
    gold_agree: int
    gold_total: int
    edge_cases: int


def build_worklist(
    store: LexiconStore,
    language: str,
    *,
    size: int = DEFAULT_WORKLIST_SIZE,
    skip: Sequence[str] = (),
) -> list[SenseWorkItem]:
    """Return the most frequent single-word cards of a language, ranked from 0.

    The cards come in pages of `MAX_CARD_LIMIT`, each excluding the lemmas
    already taken, so the order is the cards' own frequency order.

    Args:
        store: The lexicon store.
        language: The cards' language.
        size: Cards to take.
        skip: Lemma ids to leave out (the gold lemmas, already labelled).

    Returns:
        The worklist.
    """
    taken = list(skip)
    items: list[SenseWorkItem] = []
    while len(items) < size:
        query = CardQuery(
            language=language,
            single_word=True,
            order="frequency",
            exclude_ids=taken,
            limit=min(MAX_CARD_LIMIT, size - len(items)),
        )
        page = store.lemma_cards(query)
        if not page:
            break
        for card in page:
            taken.append(card.lemma.id)
            items.append(
                SenseWorkItem(
                    rank=len(items),
                    lemma_id=card.lemma.id,
                    lemma_text=card.lemma.text,
                    language=language,
                    sense_frequency=card.sense_frequency,
                )
            )
    return items


def load_worklist(data_fol: Path) -> list[SenseWorkItem]:
    """Read the committed worklist (empty when it does not exist)."""
    path = curated_path(data_fol, WORKLIST_FILE)
    return read_jsonl(SenseWorkItem, path) if path.exists() else []


def load_gold(data_fol: Path) -> list[SenseGold]:
    """Read the committed gold set, the latest row per lemma (empty when absent).

    A later row for a lemma replaces its answer (a rule change can move what a
    right card is), and the earlier row stays in the file as history.
    """
    path = curated_path(data_fol, GOLD_FILE)
    latest: dict[str, SenseGold] = {}
    for row in read_jsonl(SenseGold, path) if path.exists() else []:
        latest.pop(row.lemma_id, None)
        latest[row.lemma_id] = row
    return list(latest.values())


def parse_labels(
    batch: str,
    text: str,
    sense_counts: Mapping[int, int],
    removed: Collection[int] = (),
) -> dict[int, SenseLabel]:
    """Parse and validate a batch's label lines.

    Args:
        batch: The batch id (for the error message).
        text: The label lines (see the module docstring); blank lines and ``#``
            comments are ignored.
        sense_counts: Item number -> how many senses it showed.
        removed: Item numbers of removed lemmas, which take ``k`` or ``a`` only.

    Returns:
        Item number -> label.

    Raises:
        LabelError: Listing every unparseable line, unknown or repeated
            number, sense out of range, conflicting action, drop or addition
            without a reason, form note without an addition, and missing item.
    """
    labels: dict[int, SenseLabel] = {}
    problems: list[str] = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        n, label, line_problems = _parse_line(line, sense_counts, removed)
        problems += line_problems
        if n is None or label is None:
            continue
        if n in labels:
            problems.append(f"item {n} is labelled twice")
        labels[n] = label
    missing = sorted(set(sense_counts) - set(labels))
    if missing:
        problems.append(f"missing item(s) {', '.join(map(str, missing))}")
    if problems:
        raise LabelError(batch, problems)
    return labels


def _parse_line(
    line: str, sense_counts: Mapping[int, int], removed: Collection[int]
) -> tuple[int | None, SenseLabel | None, list[str]]:
    """Parse one label line into its item number, label and problems."""
    words = line.split()
    if not words[0].isdigit():
        return None, None, [f"unparseable line {line.strip()!r}"]
    n = int(words[0])
    if n not in sense_counts:
        return None, None, [f"item {n} is not in the batch"]
    actions: list[str] = []
    edge_case = False
    rest = words[1:]
    while rest and (match := _ACTION_RE.match(rest[0])):
        actions.append(match[1])
        edge_case |= bool(match[2])
        rest = rest[1:]
    if not actions:
        return None, None, [f"item {n} has no action in {line.strip()!r}"]
    letters = [action[0] for action in actions]
    rest_text = " ".join(rest)
    notes = _FORM_NOTE_RE.findall(rest_text)
    label = SenseLabel(
        drop_all=letters == ["x"],
        form_note=notes[0].strip() if notes else "",
        reason=" ".join(_FORM_NOTE_RE.sub(" ", rest_text).split()),
        edge_case=edge_case,
    )
    for action in actions:
        if action[0] == "p":
            label.pin = int(action[1:])
        elif action[0] == "d":
            label.drops = sorted({int(k) for k in action[1:].split(",")})
        elif action[0] == "a":
            label.add = action[1:]
    problems = _label_problems(n, label, letters, sense_counts[n])
    problems += _extra_problems(n, letters, removed=n in removed, notes=len(notes))
    return n, label, problems


def _extra_problems(
    n: int, letters: Sequence[str], *, removed: bool, notes: int
) -> list[str]:
    """Return the problems of a removed item's label and of repeated form notes."""
    problems: list[str] = []
    if removed and not set(letters) <= {"k", "a"}:
        problems.append(f"item {n}: a removed lemma takes k or a")
    if notes > 1:
        problems.append(f"item {n}: at most one form note")
    return problems


def _label_problems(
    n: int, label: SenseLabel, letters: Sequence[str], count: int
) -> list[str]:
    """Return what is wrong with one parsed label (empty when it is valid)."""
    problems: list[str] = []
    if ("k" in letters or "x" in letters) and len(letters) > 1:
        problems.append(f"item {n}: k and x stand alone")
    if letters.count("p") > 1 or letters.count("d") > 1 or letters.count("a") > 1:
        problems.append(f"item {n}: at most one p, one d and one a")
    if "a" in letters and "p" in letters:
        problems.append(f"item {n}: a pins the added sense, so no p")
    if label.form_note and label.add is None:
        problems.append(f"item {n}: a form note needs an addition")
    numbers = [*label.drops, *([label.pin] if label.pin is not None else [])]
    if any(not 1 <= k <= count for k in numbers):
        problems.append(f"item {n}: a sense outside 1-{count}")
    if label.pin is not None and label.pin in label.drops:
        problems.append(f"item {n}: sense {label.pin} is both pinned and dropped")
    if count and len(label.drops) == count and label.add is None:
        problems.append(f"item {n}: every sense dropped, use x")
    if (label.drops or label.drop_all) and not label.reason:
        problems.append(f"item {n}: a drop needs a reason")
    if label.add is not None and not label.reason:
        problems.append(f"item {n}: an addition needs a reason")
    return problems


def _reviewed_ids(data_fol: Path) -> set[str]:
    path = curated_path(data_fol, BEST_SENSES_FILE)
    rows = read_jsonl(BestSense, path) if path.exists() else []
    return {row.lemma_id for row in rows}


def _log_rows(data_fol: Path) -> list[SenseReviewLogRow]:
    path = curated_path(data_fol, REVIEW_LOG_FILE)
    return read_jsonl(SenseReviewLogRow, path) if path.exists() else []


def _shadow_log_rows(data_fol: Path) -> list[SenseReviewLogRow]:
    path = curated_path(data_fol, SHADOW_LOG_FILE)
    return read_jsonl(SenseReviewLogRow, path) if path.exists() else []


def _pending(
    data_fol: Path, subdir: str = WORK_SUBDIR
) -> dict[str, list[SenseBatchItem]]:
    return {
        path.stem: read_jsonl(SenseBatchItem, path)
        for path in sorted(work_dir(data_fol, subdir).glob("*.jsonl"))
    }


def _options(store: LexiconStore, lemma_id: str) -> list[SenseOption]:
    """Return a lemma's senses in the card's pick order."""
    return [
        SenseOption(
            concept_key=concept_key(card.concept_id),
            gloss=(card.gloss or "")[:_GLOSS_SHOWN],
            translations=card.translations.get("en", [])[:_TRANSLATIONS_SHOWN],
        )
        for card in store.lemma_sense_cards(lemma_id)
        if card.concept_id is not None
    ]


def _removed_options(
    data_fol: Path, store: LexiconStore, lemma_id: str
) -> list[SenseOption]:
    """Return the links a review dropped from a lemma no longer in the corpus."""
    options: list[SenseOption] = []
    for row in load_form_drops(data_fol):
        if row.lemma_id != lemma_id or not row.drop:
            continue
        concept = store.get_concept_by_key(row.concept_key)
        if concept is None:
            continue
        members = store.lemmas_for_concept(concept.id, "en")
        options.append(
            SenseOption(
                concept_key=row.concept_key,
                gloss=concept.definitions.get("en", "")[:_GLOSS_SHOWN],
                translations=[m.text for m in members][:_TRANSLATIONS_SHOWN],
            )
        )
    return options


def removed_lemmas(
    data_fol: Path, store: LexiconStore, language: str
) -> list[tuple[str, str]]:
    """Return ``(lemma_id, text)`` of the lemmas a review removed, by text.

    A lemma is removed when a card-sense review dropped one of its links
    (`DROP_KIND`) and the corpus no longer holds it. The gold lemmas are left
    out, as from the worklist.
    """
    gold = {row.lemma_id for row in load_gold(data_fol)}
    found = {
        row.lemma_id: row.form
        for row in load_form_drops(data_fol)
        if row.drop
        and row.kind == DROP_KIND
        and row.language == language
        and row.lemma_id not in gold
    }
    return sorted(
        ((lid, text) for lid, text in found.items() if not store.get_lemma_by_id(lid)),
        key=lambda pair: pair[1],
    )


def _pick_gold(
    data_fol: Path,
    rng: random.Random,
    *,
    language: str,
    busy: set[str],
    count: int,
) -> list[SenseGold]:
    """Pick gold lemmas, the least served first (the pool is small)."""
    served = Counter(key for row in _log_rows(data_fol) for key in row.gold_keys)
    pool = [
        gold
        for gold in load_gold(data_fol)
        if gold.language == language and gold.lemma_id not in busy
    ]
    rng.shuffle(pool)
    pool.sort(key=lambda gold: served[gold.lemma_id])
    return pool[:count]


def serve_batch(
    data_fol: Path,
    store: LexiconStore,
    *,
    batch: str,
    size: int = DEFAULT_BATCH_SIZE,
    language: str | None = None,
    gold_per_batch: int = DEFAULT_GOLD_PER_BATCH,
) -> list[SenseBatchItem]:
    """Reserve the next unreviewed worklist cards as a batch, with hidden gold.

    The batch is written under the work folder, so concurrent reviewers never
    get the same lemmas, and `apply_batch` can check the labels against the
    senses it showed. Serving an id that is already pending returns that batch
    unchanged.

    Args:
        data_fol: Project data folder.
        store: The lexicon store, for the senses.
        batch: The batch id (e.g. ``s0001``).
        size: Worklist cards to reserve.
        language: Only draw from this language (default: the first with work
            left).
        gold_per_batch: Hidden gold lemmas to mix in.

    Returns:
        The batch items, in the order the reviewer sees them (empty when the
        worklist, or the language, is done).

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
        busy = {item.lemma_id for items in pending.values() for item in items}
        taken = _reviewed_ids(data_fol) | busy
        todo = [item for item in load_worklist(data_fol) if item.lemma_id not in taken]
        if language is None and todo:
            language = todo[0].language
        picked = [item for item in todo if item.language == language][:size]
        if not picked or language is None:
            return []
        return _write_items(
            data_fol,
            store,
            batch=batch,
            picked=picked,
            busy=busy,
            gold_per_batch=gold_per_batch,
        )


def _write_items(
    data_fol: Path,
    store: LexiconStore,
    *,
    batch: str,
    picked: Sequence[SenseWorkItem],
    busy: set[str],
    gold_per_batch: int,
    subdir: str = WORK_SUBDIR,
) -> list[SenseBatchItem]:
    """Mix hidden gold into ``picked``, shuffle, and write the batch file.

    A lemma the corpus no longer holds is served with the links the review
    dropped from it. Must run under `review_batches.locked`.
    """
    language = picked[0].language
    rng = random.Random(batch)  # noqa: S311 - a reproducible shuffle, not crypto
    gold = _pick_gold(
        data_fol,
        rng,
        language=language,
        busy=busy | {item.lemma_id for item in picked},
        count=gold_per_batch,
    )
    entries: list[tuple[str, str, int | None, list[str] | None]] = [
        (item.lemma_id, item.lemma_text, item.rank, None) for item in picked
    ]
    entries += [(g.lemma_id, g.lemma_text, None, g.best) for g in gold]
    rng.shuffle(entries)
    items = []
    for n, (lid, text, rank, gold_best) in enumerate(entries, start=1):
        lemma = store.get_lemma_by_id(lid)
        items.append(
            SenseBatchItem(
                n=n,
                lemma_id=lid,
                lemma_text=text,
                language=language,
                part_of_speech=lemma.part_of_speech if lemma else None,
                senses=(
                    _options(store, lid)
                    if lemma
                    else _removed_options(data_fol, store, lid)
                ),
                rank=rank,
                gold_best=gold_best,
                removed=lemma is None,
            )
        )
    append_rows(work_dir(data_fol, subdir) / f"{batch}.jsonl", items)
    lg.info(
        "Served batch {}: {} {} card(s) + {} gold",
        batch,
        len(picked),
        language,
        len(gold),
    )
    return items


def recheck_batch(
    data_fol: Path,
    store: LexiconStore,
    *,
    batch: str,
    lemma_ids: Sequence[str],
    guide_path: Path,
    size: int = DEFAULT_BATCH_SIZE,
    gold_per_batch: int = DEFAULT_GOLD_PER_BATCH,
    shadow: bool = False,
) -> list[SenseBatchItem]:
    """Serve reviewed worklist lemmas again, as a re-check or a second review.

    A re-check picks the next ``size`` of ``lemma_ids`` that are on the worklist,
    not pending, and whose latest `BestSense` row was not written under the
    current guide; `apply_batch` then appends rows, and the latest row wins.

    A second review (``shadow``) picks the next ones not yet in a second-review
    batch, whatever their rows, and is applied with ``shadow=True``: it writes
    no curated row, only its outcomes, for `agreement` with the first review.

    Args:
        data_fol: Project data folder.
        store: The lexicon store, for the senses.
        batch: The batch id (e.g. ``m0001``, or ``n0001`` for a second review).
        lemma_ids: The lemmas to serve, in order.
        guide_path: The review guide; a re-check skips rows under its hash.
        size: Lemmas to reserve.
        gold_per_batch: Hidden gold lemmas to mix in.
        shadow: Serve a second review.

    Returns:
        The batch items (empty when every lemma is done or pending).

    Raises:
        ValueError: When the batch id was already applied.
    """
    subdir = SHADOW_SUBDIR if shadow else WORK_SUBDIR
    with locked(data_fol, WORK_SUBDIR):
        pending = _pending(data_fol, subdir)
        if batch in pending:
            return pending[batch]
        logs = _shadow_log_rows(data_fol) if shadow else _log_rows(data_fol)
        if any(row.batch == batch for row in logs):
            msg = f"batch {batch} was already applied"
            raise ValueError(msg)
        busy = {item.lemma_id for items in pending.values() for item in items}
        if shadow:
            done = {lid for row in logs for lid in row.outcomes}
        else:
            sha = guide_sha(guide_path)
            path = curated_path(data_fol, BEST_SENSES_FILE)
            latest = {
                row.lemma_id: row.prompt_sha
                for row in (read_jsonl(BestSense, path) if path.exists() else [])
            }
            done = {lid for lid, row_sha in latest.items() if row_sha == sha}
        by_id = {item.lemma_id: item for item in load_worklist(data_fol)}
        picked = [
            by_id[lid]
            for lid in lemma_ids
            if lid in by_id and lid not in busy and lid not in done
        ][:size]
        if not picked:
            return []
        return _write_items(
            data_fol,
            store,
            batch=batch,
            picked=picked,
            busy=busy,
            gold_per_batch=gold_per_batch,
            subdir=subdir,
        )


def render_batch(items: Sequence[SenseBatchItem]) -> str:
    """Return the batch as the lines a reviewer reads (gold looks the same)."""
    lines: list[str] = []
    for item in items:
        pos = f" ({item.part_of_speech})" if item.part_of_speech else ""
        removed = " REMOVED, its dropped links:" if item.removed else ""
        lines.append(f"{item.n} {item.language} {item.lemma_text}{pos}{removed}")
        lines += [
            f"  {k} {sense.gloss} [{', '.join(sense.translations)}]"
            for k, sense in enumerate(item.senses, start=1)
        ]
    return "\n".join(lines)


def apply_batch(
    data_fol: Path,
    batch: str,
    labels_text: str,
    *,
    guide_path: Path,
    store: LexiconStore | None = None,
    shadow: bool = False,
) -> SenseReviewLogRow:
    """Validate a batch's labels and record them.

    Worklist items become one accepted `BestSense` row each, one accepted
    `FormDrop` row per dropped sense, and one accepted `SenseAddition` per added
    link (whose sense the `BestSense` row pins); hidden gold items only count
    toward the agreement. Nothing is written when a label is invalid.

    A second-review batch (``shadow``) writes no curated row: its log row, with
    the outcome of every item, goes to the second-review log for `agreement`.

    Args:
        data_fol: Project data folder.
        batch: The served batch id.
        labels_text: The reviewer's label lines.
        guide_path: The review guide, hashed into every row.
        store: The lexicon store, to check an added concept exists; needed only
            when a label adds a link.
        shadow: Apply a second-review batch.

    Returns:
        The batch's log row (also appended to the review log).

    Raises:
        LabelError: When the labels do not validate.
        FileNotFoundError: When no such batch is pending.
    """
    subdir = SHADOW_SUBDIR if shadow else WORK_SUBDIR
    with locked(data_fol, WORK_SUBDIR):
        path = work_dir(data_fol, subdir) / f"{batch}.jsonl"
        if not path.exists():
            msg = f"no pending batch {batch} under {path.parent}"
            raise FileNotFoundError(msg)
        items = read_jsonl(SenseBatchItem, path)
        labels = parse_labels(
            batch,
            labels_text,
            {item.n: len(item.senses) for item in items},
            removed=[item.n for item in items if item.removed],
        )
        _check_additions(batch, items, labels, store)
        sha = guide_sha(guide_path)
        pins: list[BestSense] = []
        drops: list[FormDrop] = []
        additions: list[SenseAddition] = []
        log = SenseReviewLogRow(batch=batch, language=items[0].language, items=0)
        log.guide_sha = sha
        for item in items:
            label = labels[item.n]
            card = label.card([] if item.removed else item.senses)
            if item.gold_best is not None:
                log.gold_keys.append(item.lemma_id)
                agree = card in item.gold_best if item.gold_best else card is None
                if agree:
                    log.gold_agree += 1
                else:
                    gold = ",".join(item.gold_best) or "no card"
                    log.gold_misses.append(
                        f"{item.lemma_text}: {gold} -> {card or 'no card'}"
                    )
                continue
            dropped = (
                list(range(1, len(item.senses) + 1)) if label.drop_all else label.drops
            )
            pinned = item.senses[label.pin - 1] if label.pin is not None else None
            log.items += 1
            log.kept += not dropped and pinned is None and label.add is None
            log.pinned += pinned is not None
            log.dropped_senses += len(dropped)
            log.dropped_lemmas += label.drop_all
            log.added += label.add is not None
            log.edge_cases += label.edge_case
            log.outcomes[item.lemma_id] = SenseOutcome(
                lemma_text=item.lemma_text,
                kept=not dropped and pinned is None and label.add is None,
                card=card,
                drops=sorted(item.senses[k - 1].concept_key for k in dropped),
                add=label.add,
            )
            pin, item_drops, addition = _item_rows(
                item, label, dropped, pinned, sha=sha, batch=batch
            )
            pins.append(pin)
            drops += item_drops
            additions += [addition] if addition else []
        if shadow:
            append_rows(curated_path(data_fol, SHADOW_LOG_FILE), [log])
        else:
            append_rows(curated_path(data_fol, BEST_SENSES_FILE), pins)
            append_rows(curated_path(data_fol, MEMBER_FORM_DROPS_FILE), drops)
            append_rows(curated_path(data_fol, SENSE_ADDITIONS_FILE), additions)
            append_rows(curated_path(data_fol, REVIEW_LOG_FILE), [log])
        path.unlink()
        lg.info(
            "Applied {}batch {}: {} lemma(s), {} pin(s), {} drop(s), {} addition(s),"
            " gold {}/{}",
            "second-review " if shadow else "",
            batch,
            log.items,
            log.pinned,
            log.dropped_senses,
            log.added,
            log.gold_agree,
            len(log.gold_keys),
        )
        return log


def _item_rows(
    item: SenseBatchItem,
    label: SenseLabel,
    dropped: Sequence[int],
    pinned: SenseOption | None,
    *,
    sha: str,
    batch: str,
) -> tuple[BestSense, list[FormDrop], SenseAddition | None]:
    """Return the curated rows one worklist item's label writes."""
    pin = BestSense(
        lemma_id=item.lemma_id,
        concept_key=label.add or (pinned.concept_key if pinned else None),
        lemma_text=item.lemma_text,
        language=item.language,
        status="accepted",
        model=REVIEW_MODEL,
        prompt_sha=sha,
        batch=batch,
        edge_case=label.edge_case,
    )
    drops = [
        FormDrop(
            lemma_id=item.lemma_id,
            concept_key=item.senses[k - 1].concept_key,
            language=item.language,
            form=item.lemma_text,
            kind=DROP_KIND,
            drop=True,
            reason=label.reason,
            status="accepted",
            model=REVIEW_MODEL,
            prompt_sha=sha,
            batch=batch,
        )
        for k in dropped
    ]
    addition = (
        SenseAddition(
            lemma_id=item.lemma_id,
            concept_key=label.add,
            word=item.lemma_text,
            language=item.language,
            form_note=label.form_note,
            reason=label.reason,
            status="accepted",
            model=REVIEW_MODEL,
            prompt_sha=sha,
            batch=batch,
        )
        if label.add is not None
        else None
    )
    return pin, drops, addition


def _check_additions(
    batch: str,
    items: Sequence[SenseBatchItem],
    labels: Mapping[int, SenseLabel],
    store: LexiconStore | None,
) -> None:
    """Raise when an added concept does not exist or the word is closed-class."""
    problems: list[str] = []
    for item in items:
        key = labels[item.n].add
        if key is None:
            continue
        if store is None:
            problems.append(f"item {item.n}: an addition needs the store to check it")
        elif store.get_concept_by_key(key) is None:
            problems.append(f"item {item.n}: no concept {key}")
        if item.lemma_text.lower() in CLOSED_CLASS.get(item.language, frozenset()):
            problems.append(
                f"item {item.n}: {item.lemma_text!r} is a closed-class word, "
                "which the build keeps without senses"
            )
    if problems:
        raise LabelError(batch, problems)


def import_gold(data_fol: Path, store: LexiconStore) -> int:
    """Record the gold lemmas not yet reviewed as reviewed rows; return how many.

    A gold lemma with right senses pins the first of them, and adds the link
    when the lemma lacks it (a gold item for the review's ``a`` action); one
    without drops every sense the store holds for it.
    """
    with locked(data_fol, WORK_SUBDIR):
        reviewed = _reviewed_ids(data_fol)
        pins: list[BestSense] = []
        drops: list[FormDrop] = []
        additions: list[SenseAddition] = []
        for gold in load_gold(data_fol):
            if gold.lemma_id in reviewed:
                continue
            linked = {option.concept_key for option in _options(store, gold.lemma_id)}
            if gold.best and gold.best[0] not in linked:
                additions.append(
                    SenseAddition(
                        lemma_id=gold.lemma_id,
                        concept_key=gold.best[0],
                        word=gold.lemma_text,
                        language=gold.language,
                        reason=gold.reason,
                        status="accepted",
                        model="manual",
                        batch="gold",
                    )
                )
            pins.append(
                BestSense(
                    lemma_id=gold.lemma_id,
                    concept_key=gold.best[0] if gold.best else None,
                    lemma_text=gold.lemma_text,
                    language=gold.language,
                    status="accepted",
                    model="manual",
                    batch="gold",
                )
            )
            if not gold.best:
                drops += [
                    FormDrop(
                        lemma_id=gold.lemma_id,
                        concept_key=sense.concept_key,
                        language=gold.language,
                        form=gold.lemma_text,
                        kind=DROP_KIND,
                        drop=True,
                        reason=gold.reason,
                        status="accepted",
                        model="manual",
                        batch="gold",
                    )
                    for sense in _options(store, gold.lemma_id)
                ]
        append_rows(curated_path(data_fol, BEST_SENSES_FILE), pins)
        append_rows(curated_path(data_fol, MEMBER_FORM_DROPS_FILE), drops)
        append_rows(curated_path(data_fol, SENSE_ADDITIONS_FILE), additions)
        return len(pins)


def restore_drops(
    data_fol: Path,
    word: str,
    language: str,
    *,
    reason: str,
    keys: Sequence[str] = (),
) -> list[FormDrop]:
    """Retract a lemma's applied drops; return the retracting rows written.

    Each retracting row repeats the drop's key with ``drop: false``, and the
    latest row per key wins (`form_review.load_form_drops`), so the sense is
    back at the next build, and with it a lemma that had lost every sense.

    Args:
        data_fol: Project data folder.
        word: The lemma's text, exactly as stored.
        language: The lemma's language.
        reason: Why the drop was wrong, kept on the rows.
        keys: Only these concept keys; every applied drop of the lemma when empty.

    Raises:
        CorrectionError: When the lemma has no applied drop, or a key is not one.
    """
    target = lemma_id(word, language)
    with locked(data_fol, WORK_SUBDIR):
        dropped = {
            row.concept_key: row
            for row in load_form_drops(data_fol)
            if row.lemma_id == target and row.drop
        }
        wanted = list(keys) or list(dropped)
        unknown = [key for key in wanted if key not in dropped]
        if not wanted or unknown:
            raise CorrectionError(
                language, word, f"no applied drop for {unknown or 'any sense'}"
            )
        rows = [
            dropped[key].model_copy(
                update={
                    "drop": False,
                    "reason": reason,
                    "model": CORRECTION_MODEL,
                    "prompt_sha": "",
                    "batch": CORRECTION_BATCH,
                }
            )
            for key in wanted
        ]
        append_rows(curated_path(data_fol, MEMBER_FORM_DROPS_FILE), rows)
    return rows


def drop_sense(
    data_fol: Path,
    store: LexiconStore,
    word: str,
    language: str,
    key: str,
    *,
    reason: str,
) -> FormDrop:
    """Drop one of a lemma's senses as a wrong link; return the row written.

    The hand counterpart of a review's ``d``, for a wrong link met outside a
    batch (a wrong member of a concept a reviewer looked up). A lemma left
    without a sense leaves the corpus at the next build.

    Raises:
        CorrectionError: When the corpus has no such sense for the lemma.
    """
    target = lemma_id(word, language)
    known = [option.concept_key for option in _options(store, target)]
    if key not in known:
        raise CorrectionError(language, word, f"no sense {key}, known {known}")
    row = FormDrop(
        lemma_id=target,
        concept_key=key,
        language=language,
        form=word,
        kind=DROP_KIND,
        drop=True,
        reason=reason,
        status="accepted",
        model=CORRECTION_MODEL,
        batch=CORRECTION_BATCH,
    )
    with locked(data_fol, WORK_SUBDIR):
        append_rows(curated_path(data_fol, MEMBER_FORM_DROPS_FILE), [row])
    return row


def pin_sense(
    data_fol: Path, store: LexiconStore, word: str, language: str, key: str
) -> BestSense:
    """Pin one of a lemma's senses as its card; return the row written.

    The latest row per lemma wins (`best_senses.load_best_senses`), so this
    replaces the review's verdict at the next build.

    Raises:
        CorrectionError: When the corpus has no such sense for the lemma.
    """
    target = lemma_id(word, language)
    known = [option.concept_key for option in _options(store, target)]
    if key not in known:
        raise CorrectionError(language, word, f"no sense {key}, known {known}")
    row = BestSense(
        lemma_id=target,
        concept_key=key,
        lemma_text=word,
        language=language,
        status="accepted",
        model=CORRECTION_MODEL,
        batch=CORRECTION_BATCH,
    )
    with locked(data_fol, WORK_SUBDIR):
        append_rows(curated_path(data_fol, BEST_SENSES_FILE), [row])
    return row


def add_sense(
    data_fol: Path,
    store: LexiconStore,
    word: str,
    language: str,
    key: str,
    *,
    reason: str,
    form_note: str = "",
) -> list[SenseAddition | BestSense]:
    """Link a lemma to a concept and pin it as the card; return the rows written.

    The link applies at the next build (`sense_additions`), which creates the
    lemma when the corpus lacks it; the pin keys on the concept, so it applies
    to the new sense in the same build.

    Raises:
        CorrectionError: When the concept does not exist, or the word is a
            closed-class word.
    """
    if store.get_concept_by_key(key) is None:
        raise CorrectionError(language, word, f"no concept {key}")
    if word.lower() in CLOSED_CLASS.get(language, frozenset()):
        raise CorrectionError(language, word, "a closed-class word keeps no senses")
    target = lemma_id(word, language)
    addition = SenseAddition(
        lemma_id=target,
        concept_key=key,
        word=word,
        language=language,
        form_note=form_note,
        reason=reason,
        status="accepted",
        model=CORRECTION_MODEL,
        batch=CORRECTION_BATCH,
    )
    pin = BestSense(
        lemma_id=target,
        concept_key=key,
        lemma_text=word,
        language=language,
        status="accepted",
        model=CORRECTION_MODEL,
        batch=CORRECTION_BATCH,
    )
    with locked(data_fol, WORK_SUBDIR):
        append_rows(curated_path(data_fol, SENSE_ADDITIONS_FILE), [addition])
        append_rows(curated_path(data_fol, BEST_SENSES_FILE), [pin])
    return [addition, pin]


def find_concepts(
    store: LexiconStore, word: str, *, language: str
) -> list[tuple[SenseOption, list[str]]]:
    """Return the concepts an English word names, with their members in ``language``.

    The reviewer's lookup for an addition: each concept's key, gloss and English
    members, and the lemmas of ``language`` already linked to it.
    """
    found: list[tuple[SenseOption, list[str]]] = []
    for card in store.lemma_sense_cards(
        lemma_id(word, "en"), translation_languages=("en", language)
    ):
        if card.concept_id is None:
            continue
        option = SenseOption(
            concept_key=concept_key(card.concept_id),
            gloss=card.gloss or "",
            translations=[word, *card.translations.get("en", [])][:_TRANSLATIONS_SHOWN],
        )
        found.append((option, card.translations.get(language, [])))
    return found


def agreement(
    data_fol: Path, first: Sequence[str], second: Sequence[str]
) -> SenseAgreement:
    """Compare a first review with a second (shadow) review of the same lemmas.

    Args:
        data_fol: Project data folder.
        first: Batch ids of the first review (the review log).
        second: Batch ids of the second review (the second-review log).

    Returns:
        The counts over the lemmas both reviews labelled.
    """
    outcomes_a = {
        lid: outcome
        for row in _log_rows(data_fol)
        if row.batch in first
        for lid, outcome in row.outcomes.items()
    }
    outcomes_b = {
        lid: outcome
        for row in _shadow_log_rows(data_fol)
        if row.batch in second
        for lid, outcome in row.outcomes.items()
    }
    common = sorted(set(outcomes_a) & set(outcomes_b))

    def same(a: SenseOutcome, b: SenseOutcome) -> bool:
        return (a.card, a.drops, a.add) == (b.card, b.drops, b.add)

    def describe(outcome: SenseOutcome) -> str:
        if outcome.kept:
            return "k"
        parts = [f"card {outcome.card or '-'}"]
        parts += [f"drop {','.join(outcome.drops)}"] if outcome.drops else []
        parts += [f"add {outcome.add}"] if outcome.add else []
        return " ".join(parts)

    changed = [lid for lid in common if not outcomes_a[lid].kept]
    return SenseAgreement(
        items=len(common),
        same_card=sum(outcomes_a[lid].card == outcomes_b[lid].card for lid in common),
        same_outcome=sum(same(outcomes_a[lid], outcomes_b[lid]) for lid in common),
        first_changed=len(changed),
        agree_on_changed=sum(same(outcomes_a[lid], outcomes_b[lid]) for lid in changed),
        disagreements=[
            f"{outcomes_a[lid].lemma_text}: {describe(outcomes_a[lid])}"
            f" -> {describe(outcomes_b[lid])}"
            for lid in common
            if not same(outcomes_a[lid], outcomes_b[lid])
        ],
    )


def review_status(data_fol: Path) -> SenseReviewStatus:
    """Return how far the review has come, per language."""
    reviewed = _reviewed_ids(data_fol)
    totals: Counter[str] = Counter()
    done: Counter[str] = Counter()
    for item in load_worklist(data_fol):
        totals[item.language] += 1
        done[item.language] += item.lemma_id in reviewed
    log = _log_rows(data_fol)
    return SenseReviewStatus(
        languages={lang: (done[lang], totals[lang]) for lang in sorted(totals)},
        pending=sorted(_pending(data_fol)),
        batches=len(log),
        gold_agree=sum(row.gold_agree for row in log),
        gold_total=sum(len(row.gold_keys) for row in log),
        edge_cases=sum(row.edge_cases for row in log),
    )
