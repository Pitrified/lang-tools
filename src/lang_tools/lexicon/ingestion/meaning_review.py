"""Review the pt words of a card's meaning, and its lead translation, in batches.

A meaning (a WordNet concept) lists every word linked to it, and a pt card's
meaning shows them all on a word page and among the card's synonyms. Some of
them are not other words for the meaning: a plural or an adjective's feminine
stored as a word of its own (*canais* beside *canal*, *eterna* beside *eterno*),
a word that names something else (*cachimbo*, a smoking pipe, on the conduit
meaning of *canal*), a definition pasted in as a word, a capitalised duplicate
(*Aluminio*). And a card pairs the first en word of its meaning, which the
frequency picks: an en noun that is also a frequent verb form keeps the verb's
count, so *calling* leads *career* on *carreira*. A reviewing agent (a Claude
Code session or one of its subagents, following ``.claude/skills/meaning-review/``)
labels both against the rules in ``docs/guides/meaning_review.md``.

Worklists:
    Both start from the pt cards a drill draws: single lowercase words with no
    form note and a sense frequency of `MIN_ZIPF` or more. `build_member_worklist`
    lists their meanings with two pt words or more; `build_lead_worklist` the
    meanings whose first en translation is an -ing form of an en verb, with
    another en word to pick instead. Both are ordered by concept key, a hash, so
    the first batches are a fair sample, and stored under the work folder, which
    is not committed.

Batches:
    A batch id starts with `MEMBER_PREFIX` (meanings) or `LEAD_PREFIX` (leads).
    `serve_batch` reserves the next unlabelled meanings; `apply_batch`
    validates the labels and records them. Every label gets a `MeaningLogRow`
    in ``data/curated/meaning_review_log.jsonl``, and:

    - a word labelled a form of another word of the meaning gets a
      `SenseAddition` row with its form note (``data/curated/sense_additions.jsonl``),
      so the build tags the link like a rule-made inflection;
    - a dropped word gets a `FormDrop` row for that one link (kind `DROP_KIND`,
      ``data/curated/member_form_drops.jsonl``);
    - a picked lead gets a `LeadTranslation` row
      (``data/curated/lead_translations.jsonl``).

Label format:
    One line per numbered word (meaning batches) or meaning (lead batches): the
    number, the label, an extra where the label takes one, and a reason after
    ``#``::

        12 k
        13 f canal
        14 d # a smoking pipe, not a conduit
        3 l career
        4 k
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING
from typing import Literal

from loguru import logger as lg
from pydantic import BaseModel
from pydantic import Field

from lang_tools.lexicon.concept_id import concept_key
from lang_tools.lexicon.ingestion.form_review import MEMBER_FORM_DROPS_FILE
from lang_tools.lexicon.ingestion.form_review import FormDrop
from lang_tools.lexicon.ingestion.inflections import feminine
from lang_tools.lexicon.ingestion.inflections import form_note
from lang_tools.lexicon.ingestion.inflections import inflect
from lang_tools.lexicon.ingestion.inflections import plural
from lang_tools.lexicon.ingestion.lead_translations import LEAD_TRANSLATIONS_FILE
from lang_tools.lexicon.ingestion.lead_translations import LeadTranslation
from lang_tools.lexicon.ingestion.lookalikes import REVIEW_MODEL
from lang_tools.lexicon.ingestion.review_batches import LabelError
from lang_tools.lexicon.ingestion.review_batches import append_rows
from lang_tools.lexicon.ingestion.review_batches import guide_sha
from lang_tools.lexicon.ingestion.review_batches import locked
from lang_tools.lexicon.ingestion.review_batches import work_dir
from lang_tools.lexicon.ingestion.sense_additions import SENSE_ADDITIONS_FILE
from lang_tools.lexicon.ingestion.sense_additions import SenseAddition
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import read_jsonl
from lang_tools.lexicon.maintenance import write_jsonl

if TYPE_CHECKING:
    from collections.abc import Collection
    from collections.abc import Sequence
    from pathlib import Path

    from lang_tools.lexicon.card import LemmaCard
    from lang_tools.lexicon.lemma_store import LexiconStore

#: Labels of a meaning batch: keep the word, a form of another word, drop it.
MemberLabel = Literal["k", "f", "d"]
#: Labels of a lead batch: keep the first word, or name the one that leads.
LeadLabel = Literal["k", "l"]

#: Batch id prefixes, one per kind of batch.
MEMBER_PREFIX = "w"
LEAD_PREFIX = "l"
#: The language whose cards and words are reviewed, and the lead's language.
LANGUAGE = "pt"
LEAD_LANGUAGE = "en"
#: The card floor: the lowest sense frequency of a card a drill draws.
MIN_ZIPF = 2.0
#: The ordered worklists, under the data folder (rebuilt from the corpus).
MEMBER_WORKLIST_FILE = "work/meaning_review_members.jsonl"
LEAD_WORKLIST_FILE = "work/meaning_review_leads.jsonl"
#: One row per label, under ``data/curated/``.
REVIEW_LOG_FILE = "meaning_review_log.jsonl"
#: Served, not yet applied batches live here, under the data folder.
WORK_SUBDIR = "work/meaning_review"
#: Meanings per batch.
DEFAULT_BATCH_SIZE = 100
#: The `FormDrop.kind` of a word this review drops.
DROP_KIND = "meaning"
#: Characters of gloss, and words per other language, shown per meaning.
_GLOSS_SHOWN = 160
_OTHERS_SHOWN = 8
#: A pt word of this many words or more is flagged as definition-like.
_LONG_WORDS = 4

_MEMBER_LABELS = frozenset({"k", "f", "d"})
_LEAD_LABELS = frozenset({"k", "l"})


class MeaningWorkItem(BaseModel):
    """One meaning of an ordered worklist.

    Attributes:
        rank: Position in the worklist (0 is reviewed first).
        concept_id: The meaning.
        cards: The pt cards it is the meaning of.
    """

    rank: int
    concept_id: str
    cards: list[str] = Field(default_factory=list)


class MemberWord(BaseModel):
    """One pt word of a served meaning.

    Attributes:
        n: The word's number in the batch, as the reviewer sees it.
        lemma_id: The lemma.
        text: Its form.
        part_of_speech: The lemma's part of speech.
        level: The CEFR band of the word in this meaning.
        hint: What a rule noticed (``plural of "canal"``), or empty.
    """

    n: int
    lemma_id: str
    text: str
    part_of_speech: str | None = None
    level: str | None = None
    hint: str = ""


class MeaningItem(BaseModel):
    """One served meaning of a meaning batch.

    Attributes:
        concept_key: The meaning (`concept_key`).
        gloss: Its English gloss.
        cards: The pt cards it is the meaning of.
        en: Its English words, in card order.
        it: Its Italian words, in card order.
        words: Its pt words, numbered.
    """

    concept_key: str
    gloss: str = ""
    cards: list[str] = Field(default_factory=list)
    en: list[str] = Field(default_factory=list)
    it: list[str] = Field(default_factory=list)
    words: list[MemberWord] = Field(default_factory=list)


class LeadOption(BaseModel):
    """One en word a lead can be.

    Attributes:
        lemma_id: The lemma.
        text: Its form.
    """

    lemma_id: str
    text: str


class LeadItem(BaseModel):
    """One served meaning of a lead batch.

    Attributes:
        n: The meaning's number in the batch.
        concept_key: The meaning (`concept_key`).
        gloss: Its English gloss.
        cards: The pt cards it is the meaning of.
        options: Its en words in card order; the first is the current lead.
    """

    n: int
    concept_key: str
    gloss: str = ""
    cards: list[str] = Field(default_factory=list)
    options: list[LeadOption] = Field(default_factory=list)


class ParsedLabel(BaseModel):
    """One parsed label line.

    Attributes:
        label: The label letter.
        extra: The base word (``f``) or the leading word (``l``).
        reason: Why, after ``#``.
    """

    label: str
    extra: str = ""
    reason: str = ""


class MeaningLogRow(BaseModel):
    """One label (a line of the review log).

    Attributes:
        batch: The batch id.
        concept_key: The meaning.
        lemma_id: The labelled word (meaning batches) or the picked lead.
        text: Its form.
        label: The label letter.
        extra: The base word (``f``) or the leading word (``l``).
        reason: The reviewer's reason.
        rulebook_sha: Hash of the rulebook the batch was labelled against.
    """

    batch: str
    concept_key: str
    lemma_id: str = ""
    text: str = ""
    label: str
    extra: str = ""
    reason: str = ""
    rulebook_sha: str = ""


class MeaningReviewStatus(BaseModel):
    """Progress of one kind of batch.

    Attributes:
        worklist: Meanings on the worklist.
        reviewed: Worklist meanings with labels.
        labels: Label letter -> labels with it.
        pending: Served batch ids not yet applied.
        batches: Applied batches.
    """

    worklist: int
    reviewed: int
    labels: dict[str, int]
    pending: list[str]
    batches: int


class UnknownBatchKindError(ValueError):
    """Raised when a batch id starts with neither batch prefix."""

    def __init__(self, batch: str) -> None:
        """Initialize with the batch id.

        Args:
            batch: The id.
        """
        super().__init__(
            f"batch {batch!r} starts with neither {MEMBER_PREFIX!r} (meanings) "
            f"nor {LEAD_PREFIX!r} (leads)"
        )


# --- Worklists -----------------------------------------------------------


def drill_cards(store: LexiconStore) -> list[LemmaCard]:
    """Return the pt cards a drill draws, with their en, it and pt words.

    A card qualifies when its lemma is one lowercase alphabetic token, it has no
    form note, and its sense frequency is `MIN_ZIPF` or more.
    """
    cards = []
    for lemma in store.get_lemmas_by_language(LANGUAGE):
        if not (lemma.text.isalpha() and lemma.text == lemma.text.lower()):
            continue
        card = store.lemma_card(
            lemma.id, translation_languages=(LEAD_LANGUAGE, "it", LANGUAGE)
        )
        if (
            card is not None
            and card.concept_id is not None
            and card.form_note is None
            and (card.sense_frequency or 0.0) >= MIN_ZIPF
        ):
            cards.append(card)
    return cards


def _by_concept(cards: Sequence[LemmaCard]) -> dict[str, list[LemmaCard]]:
    out: dict[str, list[LemmaCard]] = {}
    for card in cards:
        out.setdefault(card.concept_id or "", []).append(card)
    return out


def _worklist(
    groups: dict[str, list[LemmaCard]], concept_ids: Collection[str]
) -> list[MeaningWorkItem]:
    ordered = sorted(concept_ids, key=concept_key)
    return [
        MeaningWorkItem(
            rank=rank,
            concept_id=cid,
            cards=sorted(card.lemma.text for card in groups[cid]),
        )
        for rank, cid in enumerate(ordered)
    ]


def build_member_worklist(cards: Sequence[LemmaCard]) -> list[MeaningWorkItem]:
    """Return the cards' meanings that have two pt words or more.

    Args:
        cards: The drill cards, from `drill_cards`.

    Returns:
        The worklist, ranked from 0 by concept key.
    """
    groups = _by_concept(cards)
    # A card's pt translations are the meaning's other pt words.
    picked = [cid for cid, group in groups.items() if group[0].translations[LANGUAGE]]
    lg.info("Meaning worklist: {} of {} card meaning(s)", len(picked), len(groups))
    return _worklist(groups, picked)


def is_verb_form(text: str, verbs: Collection[str]) -> bool:
    """Return True for an en -ing form of a verb in ``verbs``.

    The stem is tried as written, with a final *e* (*making*), and with a
    doubled last consonant undone (*running*).
    """
    if " " in text or not text.endswith("ing"):
        return False
    stem = text[:-3]
    return (
        stem in verbs
        or stem + "e" in verbs
        or (len(stem) > 2 and stem[-1] == stem[-2] and stem[:-1] in verbs)  # noqa: PLR2004
    )


def build_lead_worklist(
    store: LexiconStore, cards: Sequence[LemmaCard]
) -> list[MeaningWorkItem]:
    """Return the cards' meanings led by an en -ing verb form, with an alternative.

    Args:
        store: The lexicon store, for the en verbs.
        cards: The drill cards, from `drill_cards`.

    Returns:
        The worklist, ranked from 0 by concept key.
    """
    verbs = {
        lemma.text
        for lemma in store.get_lemmas_by_language(LEAD_LANGUAGE)
        if lemma.part_of_speech == "verb"
    }
    groups = _by_concept(cards)
    picked = []
    for cid, group in groups.items():
        words = group[0].translations[LEAD_LANGUAGE]
        if len(words) > 1 and is_verb_form(words[0], verbs):
            picked.append(cid)
    lg.info("Lead worklist: {} of {} card meaning(s)", len(picked), len(groups))
    return _worklist(groups, picked)


def _worklist_file(prefix: str) -> str:
    return MEMBER_WORKLIST_FILE if prefix == MEMBER_PREFIX else LEAD_WORKLIST_FILE


def save_worklist(
    data_fol: Path, prefix: str, items: Sequence[MeaningWorkItem]
) -> Path:
    """Write one kind's worklist under the data folder; return its path."""
    return write_jsonl(items, data_fol / _worklist_file(prefix))


def load_worklist(data_fol: Path, prefix: str) -> list[MeaningWorkItem]:
    """Read one kind's worklist (empty when it does not exist)."""
    path = data_fol / _worklist_file(prefix)
    return read_jsonl(MeaningWorkItem, path) if path.exists() else []


# --- Forms ---------------------------------------------------------------


def form_of(word: str, base: str, part_of_speech: str | None) -> str | None:
    """Return the form note of ``word`` as a form of ``base``, if the rules make it.

    The rules of `ingestion.inflections` are tried for a noun and for an
    adjective, the word's own class first: a plural, or an adjective's feminine
    and plurals.

    Returns:
        The note (``plural of "canal"``), or None when neither class makes the
        word from the base.
    """
    classes = ["noun", "adjective"]
    if part_of_speech == "adjective":
        classes.reverse()
    for cls in classes:
        readings = [reading for form, reading in inflect(base, cls) if form == word]
        if readings:
            return form_note(readings)
    return None


def _hint(text: str, others: Collection[str]) -> str:
    """Return what the rules notice about a pt word among its meaning's words."""
    for base in others:
        if base == text or " " in base:
            continue
        if plural(base) == text:
            return f'plural of "{base}"'
        if feminine(base) in {text, text[:-1]} and text.endswith(("a", "as")):
            return f'feminine of "{base}"'
    if text[:1].isupper():
        return "capitalised"
    if len(text.split()) >= _LONG_WORDS:
        return "definition-like"
    return ""


# --- Serving -------------------------------------------------------------


def _kind(batch: str) -> str:
    if batch.startswith(MEMBER_PREFIX):
        return MEMBER_PREFIX
    if batch.startswith(LEAD_PREFIX):
        return LEAD_PREFIX
    raise UnknownBatchKindError(batch)


def _log_rows(data_fol: Path) -> list[MeaningLogRow]:
    path = curated_path(data_fol, REVIEW_LOG_FILE)
    return read_jsonl(MeaningLogRow, path) if path.exists() else []


def _pending_paths(data_fol: Path, prefix: str) -> list[Path]:
    return sorted(work_dir(data_fol, WORK_SUBDIR).glob(f"{prefix}*.jsonl"))


def _read_batch(path: Path, prefix: str) -> list[MeaningItem] | list[LeadItem]:
    if prefix == MEMBER_PREFIX:
        return read_jsonl(MeaningItem, path)
    return read_jsonl(LeadItem, path)


def _pending_keys(data_fol: Path, prefix: str) -> set[str]:
    return {
        item.concept_key
        for path in _pending_paths(data_fol, prefix)
        for item in _read_batch(path, prefix)
    }


def _reviewed_keys(data_fol: Path, prefix: str) -> set[str]:
    return {row.concept_key for row in _log_rows(data_fol) if row.batch[0] == prefix}


def _gloss(store: LexiconStore, work: MeaningWorkItem) -> str:
    concept = store.get_concept_by_id(work.concept_id)
    return concept.definitions.get("en", "")[:_GLOSS_SHOWN] if concept else ""


def _translations(store: LexiconStore, work: MeaningWorkItem) -> dict[str, list[str]]:
    """Return the meaning's en and it words in card order, from one of its cards."""
    lemma = next(
        lemma
        for lemma in store.lemmas_for_concept(work.concept_id, LANGUAGE)
        if lemma.text == work.cards[0]
    )
    card = store.lemma_card(lemma.id, translation_languages=(LEAD_LANGUAGE, "it"))
    return card.translations if card is not None else {}


def _meaning_item(
    store: LexiconStore, work: MeaningWorkItem, first_n: int
) -> MeaningItem:
    pt: list[tuple[str, str, str | None, str | None]] = []
    for sense in store.senses_for_concept(work.concept_id):
        lemma = store.get_lemma_by_id(sense.lemma_id)
        if lemma is None or lemma.language != LANGUAGE or sense.form_note:
            continue
        pt.append((lemma.id, lemma.text, lemma.part_of_speech, sense.cefr_level))
    pt.sort(key=lambda row: row[1])
    texts = [row[1] for row in pt]
    translations = _translations(store, work)
    return MeaningItem(
        concept_key=concept_key(work.concept_id),
        gloss=_gloss(store, work),
        cards=work.cards,
        en=translations.get(LEAD_LANGUAGE, [])[:_OTHERS_SHOWN],
        it=translations.get("it", [])[:_OTHERS_SHOWN],
        words=[
            MemberWord(
                n=first_n + i,
                lemma_id=lid,
                text=text,
                part_of_speech=pos,
                level=level,
                hint=_hint(text, texts),
            )
            for i, (lid, text, pos, level) in enumerate(pt)
        ],
    )


def _lead_item(store: LexiconStore, work: MeaningWorkItem, n: int) -> LeadItem:
    words = _translations(store, work).get(LEAD_LANGUAGE, [])
    by_text = {
        lemma.text: lemma.id
        for lemma in store.lemmas_for_concept(work.concept_id, LEAD_LANGUAGE)
    }
    return LeadItem(
        n=n,
        concept_key=concept_key(work.concept_id),
        gloss=_gloss(store, work),
        cards=work.cards,
        options=[LeadOption(lemma_id=by_text[text], text=text) for text in words],
    )


def serve_batch(
    data_fol: Path,
    store: LexiconStore,
    *,
    batch: str,
    size: int = DEFAULT_BATCH_SIZE,
) -> list[MeaningItem] | list[LeadItem]:
    """Reserve the next unlabelled meanings of the batch's kind.

    The batch is written under the work folder, so concurrent reviewers never
    get the same meanings, and `apply_batch` checks the labels against what it
    showed. Serving an id that is already pending returns that batch unchanged.

    Args:
        data_fol: Project data folder.
        store: The lexicon store.
        batch: The batch id (``w0001`` for meanings, ``l0001`` for leads).
        size: Meanings to reserve.

    Returns:
        The batch items (empty when the worklist is done).

    Raises:
        ValueError: When the batch id was already applied.
    """
    prefix = _kind(batch)
    with locked(data_fol, WORK_SUBDIR):
        path = work_dir(data_fol, WORK_SUBDIR) / f"{batch}.jsonl"
        if path.exists():
            return _read_batch(path, prefix)
        if any(row.batch == batch for row in _log_rows(data_fol)):
            msg = f"batch {batch} was already applied"
            raise ValueError(msg)
        taken = _reviewed_keys(data_fol, prefix) | _pending_keys(data_fol, prefix)
        todo = [
            work
            for work in load_worklist(data_fol, prefix)
            if concept_key(work.concept_id) not in taken
        ][:size]
        items: list[MeaningItem] | list[LeadItem]
        if prefix == MEMBER_PREFIX:
            meanings: list[MeaningItem] = []
            n = 1
            for work in todo:
                meanings.append(_meaning_item(store, work, n))
                n += len(meanings[-1].words)
            items = meanings
        else:
            items = [_lead_item(store, work, n) for n, work in enumerate(todo, 1)]
        if items:
            append_rows(path, items)
            lg.info("Served batch {}: {} meaning(s)", batch, len(items))
        return items


def render_batch(items: Sequence[MeaningItem] | Sequence[LeadItem]) -> str:
    """Return the batch as the lines a reviewer reads."""
    lines: list[str] = []
    for item in items:
        if isinstance(item, MeaningItem):
            lines.append(f"== {item.gloss}")
            lines.append(
                f"   cards: {', '.join(item.cards)} | en: {', '.join(item.en)}"
                f" | it: {', '.join(item.it) or '-'}"
            )
            for word in item.words:
                pos = f" {word.part_of_speech}" if word.part_of_speech else ""
                hint = f" [{word.hint}]" if word.hint else ""
                lines.append(f"{word.n} {word.text} ({word.level or '-'}{pos}){hint}")
        else:
            lines.append(f"{item.n} {', '.join(item.cards)}: {item.gloss}")
            lines.append(f"   en: {' | '.join(option.text for option in item.options)}")
    return "\n".join(lines)


# --- Labels --------------------------------------------------------------


def parse_labels(
    batch: str, text: str, numbers: Collection[int], *, letters: Collection[str]
) -> dict[int, ParsedLabel]:
    """Parse a batch's label lines: number, letter, extra, ``# reason``.

    Only the shape is checked here (known numbers, known letters, each number
    once, none missing); what an extra must be is checked by `apply_batch`,
    which knows the items.

    Raises:
        LabelError: Listing every problem at once.
    """
    labels: dict[int, ParsedLabel] = {}
    problems: list[str] = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        body, _, reason = line.partition("#")
        words = body.split()
        if not words or not words[0].isdigit():
            problems.append(f"unparseable line {line.strip()!r}")
            continue
        n = int(words[0])
        if n not in numbers:
            problems.append(f"item {n} is not in the batch")
            continue
        if len(words) < 2 or words[1] not in letters:  # noqa: PLR2004
            problems.append(f"item {n} has no known label in {line.strip()!r}")
            continue
        if n in labels:
            problems.append(f"item {n} is labelled twice")
        labels[n] = ParsedLabel(
            label=words[1], extra=" ".join(words[2:]), reason=reason.strip()
        )
    missing = sorted(set(numbers) - set(labels))
    if missing:
        problems.append(f"missing item(s) {', '.join(map(str, missing))}")
    if problems:
        raise LabelError(batch, problems)
    return labels


def _member_problems(
    item: MeaningItem, word: MemberWord, label: ParsedLabel
) -> list[str]:
    """Return what is wrong with one word's label (empty when it is valid)."""
    n = word.n
    if label.label == "k":
        return [f"item {n}: k takes nothing before the reason"] if label.extra else []
    if label.label == "d":
        problems = (
            [f"item {n}: d takes nothing before the reason"] if label.extra else []
        )
        if not label.reason:
            problems.append(f"item {n}: d needs a reason after #")
        return problems
    others = {other.text for other in item.words if other.n != n}
    if label.extra not in others:
        return [f"item {n}: f needs another pt word of the same meaning as its base"]
    if form_of(word.text, label.extra, word.part_of_speech) is None:
        return [
            f"item {n}: the rules do not make {word.text!r} from {label.extra!r}; "
            "label it k or d"
        ]
    return []


def _lead_problems(item: LeadItem, label: ParsedLabel) -> list[str]:
    n = item.n
    if label.label == "k":
        return [f"item {n}: k takes nothing before the reason"] if label.extra else []
    texts = [option.text for option in item.options]
    if label.extra not in texts:
        return [f"item {n}: l needs one of the en words shown, not {label.extra!r}"]
    if label.extra == texts[0]:
        return [f"item {n}: {label.extra!r} already leads; label it k"]
    return []


# --- Applying ------------------------------------------------------------


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
    prefix = _kind(batch)
    with locked(data_fol, WORK_SUBDIR):
        path = work_dir(data_fol, WORK_SUBDIR) / f"{batch}.jsonl"
        if not path.exists():
            msg = f"no pending batch {batch} under {path.parent}"
            raise FileNotFoundError(msg)
        sha = guide_sha(guide_path)
        if prefix == MEMBER_PREFIX:
            log = _apply_members(
                data_fol, batch, read_jsonl(MeaningItem, path), labels_text, sha
            )
        else:
            log = _apply_leads(
                data_fol, batch, read_jsonl(LeadItem, path), labels_text, sha
            )
        path.unlink()
        lg.info(
            "Applied batch {}: {} label(s) {}",
            batch,
            len(log),
            dict(sorted(Counter(row.label for row in log).items())),
        )
        return log


def _apply_members(
    data_fol: Path, batch: str, items: list[MeaningItem], text: str, sha: str
) -> list[MeaningLogRow]:
    words = [(item, word) for item in items for word in item.words]
    labels = parse_labels(
        batch, text, [word.n for _, word in words], letters=_MEMBER_LABELS
    )
    problems = [
        problem
        for item, word in words
        for problem in _member_problems(item, word, labels[word.n])
    ]
    if problems:
        raise LabelError(batch, problems)
    log: list[MeaningLogRow] = []
    forms: list[SenseAddition] = []
    drops: list[FormDrop] = []
    for item, word in words:
        label = labels[word.n]
        log.append(
            MeaningLogRow(
                batch=batch,
                concept_key=item.concept_key,
                lemma_id=word.lemma_id,
                text=word.text,
                label=label.label,
                extra=label.extra,
                reason=label.reason,
                rulebook_sha=sha,
            )
        )
        if label.label == "f":
            note = form_of(word.text, label.extra, word.part_of_speech) or ""
            forms.append(
                SenseAddition(
                    lemma_id=word.lemma_id,
                    concept_key=item.concept_key,
                    word=word.text,
                    language=LANGUAGE,
                    form_note=note,
                    reason=label.reason or f"a form of {label.extra}, not a word",
                    status="accepted",
                    model=REVIEW_MODEL,
                    prompt_sha=sha,
                    batch=batch,
                )
            )
        elif label.label == "d":
            drops.append(
                FormDrop(
                    lemma_id=word.lemma_id,
                    concept_key=item.concept_key,
                    language=LANGUAGE,
                    form=word.text,
                    kind=DROP_KIND,
                    drop=True,
                    reason=label.reason,
                    status="accepted",
                    model=REVIEW_MODEL,
                    prompt_sha=sha,
                    batch=batch,
                )
            )
    append_rows(curated_path(data_fol, SENSE_ADDITIONS_FILE), forms)
    append_rows(curated_path(data_fol, MEMBER_FORM_DROPS_FILE), drops)
    append_rows(curated_path(data_fol, REVIEW_LOG_FILE), log)
    return log


def _apply_leads(
    data_fol: Path, batch: str, items: list[LeadItem], text: str, sha: str
) -> list[MeaningLogRow]:
    labels = parse_labels(batch, text, [item.n for item in items], letters=_LEAD_LABELS)
    problems = [
        problem for item in items for problem in _lead_problems(item, labels[item.n])
    ]
    if problems:
        raise LabelError(batch, problems)
    log: list[MeaningLogRow] = []
    leads: list[LeadTranslation] = []
    for item in items:
        label = labels[item.n]
        chosen = next(
            (option for option in item.options if option.text == label.extra), None
        )
        log.append(
            MeaningLogRow(
                batch=batch,
                concept_key=item.concept_key,
                lemma_id=chosen.lemma_id if chosen else "",
                text=chosen.text if chosen else "",
                label=label.label,
                extra=label.extra,
                reason=label.reason,
                rulebook_sha=sha,
            )
        )
        if chosen is not None:
            leads.append(
                LeadTranslation(
                    concept_key=item.concept_key,
                    language=LEAD_LANGUAGE,
                    lemma_id=chosen.lemma_id,
                    word=chosen.text,
                    card_word=", ".join(item.cards),
                    status="accepted",
                    model=REVIEW_MODEL,
                    prompt_sha=sha,
                    batch=batch,
                )
            )
    append_rows(curated_path(data_fol, LEAD_TRANSLATIONS_FILE), leads)
    append_rows(curated_path(data_fol, REVIEW_LOG_FILE), log)
    return log


def review_status(data_fol: Path, prefix: str) -> MeaningReviewStatus:
    """Return how far one kind of batch has come."""
    rows = [row for row in _log_rows(data_fol) if row.batch[0] == prefix]
    worklist = {
        concept_key(work.concept_id) for work in load_worklist(data_fol, prefix)
    }
    return MeaningReviewStatus(
        worklist=len(worklist),
        reviewed=len(worklist & {row.concept_key for row in rows}),
        labels=dict(sorted(Counter(row.label for row in rows).items())),
        pending=[path.stem for path in _pending_paths(data_fol, prefix)],
        batches=len({row.batch for row in rows}),
    )
