"""Non-English gloss backfill: worklist, batching, and the acceptance check (phase 8).

OMW glosses every concept in English and almost none in the other four languages,
so a learner reading a pt / es / fr definition today reads nothing. The backfill
renders each missing gloss from the English one (`llm.gloss_translate`):

- `missing_glosses` is the worklist: every (concept, language) where the concept
  has a member word in that language and no gloss in it (174,319 on the phase-7
  corpus), with both languages' member words as grounding;
- `chunk_items` groups one language's items ~25 to a request, so a batch pays
  the instructions once per chunk instead of once per gloss;
- `check_glosses` screens each generated gloss and writes it as a
  `GlossProposal`: empty, a bare member word, the untranslated English gloss, or
  a runaway length is ``rejected``; the rest stay ``proposed``.

Acceptance is by sampled human review (phase 8 Decision 4): `review_sample`
draws a fixed sample per language, and only once a reviewer accepts the run are
its ``proposed`` rows flipped to ``accepted`` (`accept_run`) in the committed
``data/curated/gloss_backfill.jsonl``. The build fills gaps only - a source or
curated gloss always wins - and tags each generated gloss ``llm``
(`maintenance.apply_gloss_backfill`).
"""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import TYPE_CHECKING
import unicodedata

from lang_tools.lexicon.codec import LEXICON_SUBDIR
from lang_tools.lexicon.concept_id import concept_key
from lang_tools.lexicon.lemma_store import CorpusNotFoundError
from lang_tools.lexicon.maintenance import GlossProposal
from lang_tools.lexicon.maintenance import normalize_gloss
from lang_tools.lexicon.quality import _connect
from lang_tools.lexicon.quality import _table_sources
from lang_tools.llm.gloss_translate import GlossSource
from lang_tools.llm.gloss_translate import GlossTranslateInput

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Sequence
    from pathlib import Path

    from lang_tools.llm.gloss_translate import GlossTranslateOutput

#: The languages the backfill writes, with the names the prompt uses.
LANGUAGE_NAMES: dict[str, str] = {
    "fr": "French",
    "pt": "Portuguese",
    "es": "Spanish",
    "it": "Italian",
}

#: The variety each language's glosses are written in (prompt v2). Portuguese is
#: Brazilian because OpenWordnet-PT, the source of every pt lemma, is; Spanish is a
#: neutral register because the glosses are general, not regional (phase 8).
LANGUAGE_VARIETIES: dict[str, str] = {
    "fr": "standard French (France), neutral dictionary register",
    "pt": "Brazilian Portuguese (pt-BR spelling and vocabulary)",
    "es": "neutral, pan-Hispanic Spanish; avoid regionalisms",
    "it": "standard Italian, neutral dictionary register",
}

#: Concepts per request.
CHUNK_SIZE = 25

#: A gloss longer than this many times its English source is rejected as runaway.
MAX_LENGTH_RATIO = 4

#: Member words shown per side (context only).
_MEMBERS_SHOWN = 6


@dataclass(frozen=True)
class BackfillItem:
    """One missing gloss.

    Attributes:
        concept_id: The concept to gloss.
        language: The target language.
        english_definition: The English gloss to render.
        english_members: The concept's English words.
        target_members: The concept's words in `language`.
    """

    concept_id: str
    language: str
    english_definition: str
    english_members: tuple[str, ...]
    target_members: tuple[str, ...]

    @property
    def key(self) -> str:
        """The item key, ``{language}:{concept_key}``."""
        return f"{self.language}:{concept_key(self.concept_id)}"


def missing_glosses(
    data_fol: Path,
    languages: Iterable[str] = tuple(LANGUAGE_NAMES),
) -> list[BackfillItem]:
    """Return every missing gloss with its grounding, sorted by key.

    Args:
        data_fol: Project data folder; the corpus lives under ``<data_fol>/lexicon/``.
        languages: Target languages (default: every `LANGUAGE_NAMES` entry).

    Returns:
        One item per (concept, language) with a member word but no gloss in that
        language, and an English gloss to render from.

    Raises:
        CorpusNotFoundError: When no Parquet corpus exists at the location.
    """
    corpus_dir = data_fol / LEXICON_SUBDIR
    if not (corpus_dir / "concepts.parquet").exists():
        raise CorpusNotFoundError(corpus_dir)
    langs = sorted(languages)
    lang_list = "[" + ", ".join(f"'{lang}'" for lang in langs) + "]"
    t = _table_sources(data_fol)
    con = _connect()
    try:
        rows = con.execute(
            f"""
WITH members AS (
  SELECT s.concept_id, l.language, list(l.text ORDER BY l.text) AS forms
  FROM {t["senses"]} s JOIN {t["lemmas"]} l ON l.id = s.lemma_id
  GROUP BY s.concept_id, l.language
)
SELECT m.concept_id, m.language, c.definitions['en'], coalesce(e.forms, []),
       m.forms
FROM members m
JOIN {t["concepts"]} c ON c.id = m.concept_id
LEFT JOIN members e ON e.concept_id = m.concept_id AND e.language = 'en'
WHERE list_contains({lang_list}, m.language)
  AND NOT list_contains(map_keys(c.definitions), m.language)
  AND c.definitions['en'] IS NOT NULL
""",
        ).fetchall()
    finally:
        con.close()
    items = [
        BackfillItem(
            concept_id=cid,
            language=language,
            english_definition=gloss,
            english_members=tuple(en_forms[:_MEMBERS_SHOWN]),
            target_members=tuple(forms[:_MEMBERS_SHOWN]),
        )
        for cid, language, gloss, en_forms, forms in rows
    ]
    return sorted(items, key=lambda item: item.key)


def chunk_items(
    items: Sequence[BackfillItem],
    size: int = CHUNK_SIZE,
) -> list[tuple[str, GlossTranslateInput]]:
    """Group one language's items ``size`` to a request, as runner work items.

    Chunks are cut over the key-sorted items of each language, so the same
    worklist always yields the same chunks; the chunk key is its first item's key.
    """
    by_lang: dict[str, list[BackfillItem]] = {}
    for item in sorted(items, key=lambda i: i.key):
        by_lang.setdefault(item.language, []).append(item)
    chunks = []
    for language, lang_items in sorted(by_lang.items()):
        for start in range(0, len(lang_items), size):
            batch = lang_items[start : start + size]
            chunks.append(
                (
                    batch[0].key,
                    GlossTranslateInput(
                        language_name=LANGUAGE_NAMES.get(language, language),
                        variety=LANGUAGE_VARIETIES.get(language, ""),
                        concepts=[
                            GlossSource(
                                key=item.key,
                                english_definition=item.english_definition,
                                english_members=", ".join(item.english_members),
                                target_members=", ".join(item.target_members),
                            )
                            for item in batch
                        ],
                    ),
                ),
            )
    return chunks


def check_glosses(
    items: Iterable[BackfillItem],
    output: GlossTranslateOutput,
) -> list[GlossProposal]:
    """Screen one chunk's generated glosses into proposals (pure).

    Args:
        items: The chunk's items (any order).
        output: The chain's output for the chunk.

    Returns:
        One proposal per item: ``proposed`` when it passes the screen, else
        ``rejected`` with the reason in `GlossProposal.rationale`.
    """
    generated = {gloss.key: _tidy(gloss.definition) for gloss in output.glosses}
    proposals = []
    for item in items:
        text = generated.get(item.key, "")
        reason = _screen(item, text)
        proposals.append(
            GlossProposal(
                concept_id=item.concept_id,
                language=item.language,
                current_definition="",
                proposed_definition=text,
                rationale=reason,
                status="rejected" if reason else "proposed",
            ),
        )
    return proposals


def _tidy(text: str) -> str:
    """Normalize typographic hyphens the model emits (U+2010/U+2011) to ``-``."""
    return text.replace("\u2011", "-").replace("\u2010", "-").strip()


def _fold(text: str) -> str:
    """Fold a gloss or form for comparison: build-time style, no case, no accents.

    Matches what the quality gate compares (``lower(strip_accents(...))``), after
    the `normalize_gloss` the build applies, so a gloss that passes here cannot
    turn into a restated member word at build time.
    """
    decomposed = unicodedata.normalize("NFKD", normalize_gloss(text, ""))
    bare = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return bare.casefold()


def _screen(item: BackfillItem, text: str) -> str:
    """Return why a generated gloss is unusable, or ``""``."""
    if not text:
        return "missing"
    folded = _fold(text)
    if folded in {_fold(member) for member in item.target_members}:
        return "restates a member word"
    # Untranslated keeps accents: fr "Médiocre" for "mediocre" is a translation.
    if (
        normalize_gloss(text, "").casefold()
        == normalize_gloss(
            item.english_definition,
            "",
        ).casefold()
    ):
        return "untranslated"
    if len(text) > MAX_LENGTH_RATIO * max(len(item.english_definition), 20):
        return "runaway length"
    return ""


def review_sample(
    proposals: Sequence[GlossProposal],
    per_language: int = 50,
    seed: int = 0,
) -> list[GlossProposal]:
    """Draw a fixed random sample of ``proposed`` rows per language for review."""
    rng = random.Random(seed)  # noqa: S311 - a review sample, not a secret
    by_lang: dict[str, list[GlossProposal]] = {}
    for proposal in proposals:
        if proposal.status == "proposed":
            by_lang.setdefault(proposal.language, []).append(proposal)
    sample: list[GlossProposal] = []
    for _language, rows in sorted(by_lang.items()):
        sample.extend(rng.sample(rows, min(per_language, len(rows))))
    return sample


def accept_run(
    proposals: Sequence[GlossProposal],
    languages: Iterable[str] | None = None,
) -> list[GlossProposal]:
    """Return the rows with every ``proposed`` one flipped to ``accepted``.

    The reviewer's decision after reading `review_sample`, applied to the whole
    run (or to the `languages` whose sample passed). Rejected rows stay rejected.
    """
    langs = set(languages) if languages is not None else None

    def _passes(proposal: GlossProposal) -> bool:
        in_scope = langs is None or proposal.language in langs
        return proposal.status == "proposed" and in_scope

    return [
        proposal.model_copy(update={"status": "accepted"})
        if _passes(proposal)
        else proposal
        for proposal in proposals
    ]
