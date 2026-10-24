"""Look-alike pairs across languages: cognate keys and candidates (phase 11).

A **look-alike** is a pair of lemmas in two languages whose forms resemble each
other: a true cognate (pt *nação* / en *nation*), a false friend (pt *esquisito*,
weird, / en *exquisite*), a partial false friend that shares only a minor sense
(pt *assistir* / en *assist*), or coincidental noise (pt *casa* / en *cast*). This
module finds the candidates deterministically; an LLM verifier then decides the
kind and writes the learner note (see `llm.lookalike_verify`).

Cognate key:
    Raw spelling distance misses textbook traps whose spelling drifted while the
    root did not (en *factory* / it *fattoria*, en *push* / pt *puxar*). Before
    comparing, `cognate_key` rewrites a form with cross-language spelling
    correspondences: suffix families (*-tion* / *-ção* / *-zione*, *-ly* /
    *-mente*, *-ble* / *-vel* / *-bile*), sound spellings (en *sh*, pt *ch* and
    *x*, it *sci* all become ``x``; hard *c* / *qu* / *k* become ``k``), the
    Romance prothetic *e-* before *s* + consonant (pt *esquadra* / it
    *squadra*), dropped *h*, collapsed doubles and a stripped final vowel. Both
    sides of a pair go through the same rules, so the keys of related words
    converge (*factory* and *fattoria* both become ``fatori``).

The rules are a reviewable table, not a learned model; the gold set
(``data/curated/lookalike_gold.jsonl``) is what they are tuned against.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import TYPE_CHECKING
from typing import Literal

from loguru import logger as lg
import pyarrow as pa
from pydantic import BaseModel

from lang_tools.language.normalization import normalize
from lang_tools.lexicon.codec import LEXICON_SUBDIR
from lang_tools.lexicon.lemma_store import CorpusNotFoundError
from lang_tools.lexicon.maintenance import CURATED_SUBDIR
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import read_jsonl
from lang_tools.lexicon.quality import _connect
from lang_tools.lexicon.quality import _table_sources
from lang_tools.lexicon.relations import LookalikeKind
from lang_tools.lexicon.relations import LookalikeRelation
from lang_tools.llm.lookalike_verify import LookalikeVerifyInput
from lang_tools.llm.lookalike_verify import LookalikeVerifyOutput
from lang_tools.llm.lookalike_verify import PairSource

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterable
    from collections.abc import Sequence
    from pathlib import Path

    from lang_tools.lexicon.lemma_store import LexiconStore

#: Suffix rewrites, per language, applied once to the lowercase form *before*
#: accents are folded: pt *-ção* and *-cão* fold to the same letters, but only
#: the first is the *-tion* family (*nação*, not *balcão*). Each family maps to
#: the same target across languages, so *-tion*, *-ção* and *-zione* all end in
#: ``zion``. A third element limits a rule to one part of speech (*-ly* is the
#: adverb ending only on adverbs: *family* is not *famimente*).
_SUFFIXES: dict[str, tuple[tuple[str, ...], ...]] = {
    "en": (
        (r"(?:t|s)ion$", "zion"),
        (r"ally$", "almente", "adverb"),
        (r"ly$", "mente", "adverb"),
        (r"ity$", "ita"),
        (r"ty$", "ta"),
        (r"ous$", "oso"),
        (r"ble$", "bil"),
        (r"ary$", "ario"),
        (r"ment$", "mento"),
        (r"ician$", "ico"),
    ),
    "pt": (
        (r"[çs]ão$", "zion"),
        (r"ão$", "on"),
        (r"idade$", "ita"),
        (r"dade$", "ta"),
        (r"vel$", "bil"),
    ),
    "it": (
        (r"(?:z|s)ione$", "zion"),
        (r"bile$", "bil"),
    ),
}

#: Spelling-to-sound rewrites, per language, applied in order after the suffixes.
_SPELLINGS: dict[str, tuple[tuple[str, str], ...]] = {
    "en": (
        (r"^ex(?=[^aeiou])", "es"),
        (r"sch", "sk"),
        (r"sh", "x"),
        (r"ph", "f"),
        (r"th", "t"),
        # en "ch" is /k/ before r / l and in Greek loans (chaos, chemistry,
        # chorus, character), and /tS/ elsewhere, which the Romance spellings
        # write as "c(i)" / "ch" and the key writes as "x".
        (r"ch(?=[rl])|^ch(?=ao|em|or|ara)", "k"),
        (r"ch", "x"),
        (r"ee", "i"),
        (r"oo", "u"),
        (r"ea", "e"),
        (r"oa", "o"),
        (r"y", "i"),
        (r"w", "v"),
    ),
    "pt": (
        (r"ch", "x"),
        (r"lh", "l"),
        (r"nh", "n"),
    ),
    "it": (
        (r"sc(?=[ie])", "x"),
        (r"ci(?=[aou])", "x"),
        (r"gli", "li"),
        (r"gn", "n"),
        (r"ch", "k"),
    ),
}

#: Romance infinitive endings, stripped from verbs so pt *puxar* and it
#: *guardare* compare on their stems (en verbs carry no ending).
_INFINITIVES: dict[str, re.Pattern[str]] = {
    "pt": re.compile(r"(?<=..)[aei]r$"),
    "it": re.compile(r"(?<=..)[aei]re$"),
}

#: Rewrites shared by every language, applied last.
_COMMON: tuple[tuple[str, str], ...] = (
    (r"^es(?=[^aeiou])", "s"),
    (r"ct", "t"),
    (r"pt", "t"),
    (r"qu", "k"),
    (r"c(?=[aou]|$|[^eihaou])", "k"),
    (r"h", ""),
    (r"z", "s"),
)

_DOUBLE = re.compile(r"(.)\1+")
_VOWELS = re.compile(r"[aeiou]")
_FINAL_VOWELS = re.compile(r"[aeiou]+$")

#: A key never shrinks below this many characters when its final vowels go.
_MIN_KEY = 3


def fold(text: str) -> str:
    """Return the accent- and case-folded form a key is built from."""
    return normalize(text).replace("-", "").replace(" ", "")


def cognate_key(text: str, language: str, part_of_speech: str | None = None) -> str:
    """Return the cross-language comparison key of a lemma form.

    Args:
        text: The lemma form, accents and case as stored.
        language: ISO 639-1 code; ``en``, ``pt`` and ``it`` have their own
            rules, any other language gets only the shared ones.
        part_of_speech: The lemma's part of speech; a ``"verb"`` loses its
            Romance infinitive ending.

    Returns:
        A lowercase ASCII key. Related forms in different languages share or
        nearly share a key: ``cognate_key("factory", "en")`` and
        ``cognate_key("fattoria", "it")`` are both ``"fatori"``.
    """
    key = text.lower().replace("-", "").replace(" ", "")
    infinitive = _INFINITIVES.get(language)
    if part_of_speech == "verb" and infinitive is not None:
        key = infinitive.sub("", key)
    for pattern, repl, *pos in _SUFFIXES.get(language, ()):
        if pos and pos[0] != part_of_speech:
            continue
        key, hits = re.subn(pattern, repl, key)
        if hits:
            break
    # The cedilla is a soft "s" whatever follows; once folded it would read as a
    # hard "c" before a / o / u (*cabeça* would key as "kabek").
    key = fold(key.replace("ç", "s"))
    for pattern, repl in (*_SPELLINGS.get(language, ()), *_COMMON):
        key = re.sub(pattern, repl, key)
    key = _DOUBLE.sub(r"\1", key)
    stripped = _FINAL_VOWELS.sub("", key)
    return stripped if len(stripped) >= _MIN_KEY else key


def skeleton(key: str) -> str:
    """Return a key's consonant skeleton, the second blocking key.

    Blocking on the key's first two characters alone loses pairs whose first
    vowel drifted (pt *lanche* / en *lunch*) or whose initial *h* went silent
    (pt *história* / it *storia*); their consonants still line up.
    """
    return _VOWELS.sub("", key)


def key_similarity(a: str, b: str) -> float:
    """Return ``1 - levenshtein / max_length`` between two keys or forms."""
    if not a or not b:
        return 0.0
    return 1.0 - _levenshtein(a, b) / max(len(a), len(b))


def _levenshtein(a: str, b: str) -> int:
    """Return the edit distance between two short strings."""
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(
                min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)),
            )
        previous = current
    return previous[-1]


# --- Candidate generation -----------------------------------------------------


#: Lowest similarity a pair needs to become a candidate (tuned on the gold set:
#: 113 of 116 gold false friends score at least 0.7, the rest 0.67).
DEFAULT_THRESHOLD = 0.65

#: Shortest key a candidate may have; shorter keys collide by chance.
MIN_CANDIDATE_KEY = 3

#: A drill word: one lowercase alphabetic token (accents allowed), as in
#: `lemma_store._is_single_word`, written as a DuckDB regex.
_SINGLE_WORD_SQL = "^[a-zà-öø-ÿœæ]+$"


@dataclass(frozen=True)
class LookalikeCandidate:
    """One look-alike pair found by the deterministic generator.

    Attributes:
        target_id: Lemma id in the target language (the one being learned).
        target_text: Its form.
        known_id: Lemma id in the known language.
        known_text: Its form.
        known_language: ISO 639-1 code of the known side.
        similarity: Best of the key and folded-form similarities (0-1).
        kind: Provisional kind from the meaning signals; the verifier decides.
        shares_concept: Whether the two lemmas share any concept at all.
        same_key: Whether the two cognate keys are identical.
        form_similarity: Similarity of the folded forms alone; it breaks
            ties between candidates that share a key (pt *cola* is closer to
            en *cola* than to *cole*).
        same_pos: Whether the two lemmas have the same part of speech.
        known_zipf: Highest token frequency (Zipf) of the known lemma, None
            when it has none.
    """

    target_id: str
    target_text: str
    known_id: str
    known_text: str
    known_language: str
    similarity: float
    kind: LookalikeKind
    shares_concept: bool
    same_key: bool = False
    form_similarity: float = 0.0
    same_pos: bool = False
    known_zipf: float | None = None

    @property
    def key(self) -> str:
        """Return the item key, ``{target_id}:{known_id}``."""
        return f"{self.target_id}:{self.known_id}"

    @property
    def pair(self) -> tuple[str, str]:
        """Return the unordered lemma-id pair, for matching against gold."""
        a, b = sorted((self.target_id, self.known_id))
        return a, b


def find_candidates(
    data_fol: Path,
    *,
    target: str = "pt",
    known: Sequence[str] = ("en", "it"),
    threshold: float = DEFAULT_THRESHOLD,
) -> list[LookalikeCandidate]:
    """Return every look-alike candidate between a target and its known languages.

    Every single-word lemma is keyed with `cognate_key`; pairs are compared only
    within a block that shares the key's first two characters (and a similar
    length), which keeps the full word range tractable. A pair whose key or
    folded-form similarity reaches ``threshold`` becomes a candidate, with a
    provisional kind from three meaning signals:

    - **cognate** when either word realises the other's *best* concept (for two
      non-English words, also when their best concepts share an English member);
    - **partial** when they share some other concept, or an English member
      across any of their senses;
    - **full** otherwise.

    Args:
        data_fol: Project data folder; the corpus lives under ``<data_fol>/lexicon/``.
        target: The language being learned.
        known: The learner's known languages.
        threshold: Minimum similarity for a candidate.

    Returns:
        The candidates, most similar first.

    Raises:
        CorpusNotFoundError: When no Parquet corpus exists at the location.
    """
    corpus_dir = data_fol / LEXICON_SUBDIR
    if not (corpus_dir / "concepts.parquet").exists():
        raise CorpusNotFoundError(corpus_dir)
    languages = [target, *known]
    lang_list = ", ".join(f"'{lang}'" for lang in languages)
    t = _table_sources(data_fol)
    con = _connect()
    try:
        words = con.execute(
            f"""
SELECT id, text, language, part_of_speech, normalized FROM {t["lemmas"]}
WHERE language IN ({lang_list}) AND regexp_matches(text, '{_SINGLE_WORD_SQL}')
""",  # noqa: S608 - languages are ISO codes from the caller, not user input
        ).fetchall()
        keys = [cognate_key(w[1], w[2], w[3]) for w in words]
        keyed = pa.table(
            {
                "id": [w[0] for w in words],
                "text": [w[1] for w in words],
                "language": [w[2] for w in words],
                "pos": [w[3] for w in words],
                "folded": [fold(w[1]) for w in words],
                "key": keys,
                "skel": [skeleton(k) for k in keys],
            },
        )
        con.register("keyed", keyed)
        rows = con.execute(_CANDIDATE_SQL.format(**t), [target, threshold]).fetchall()
    finally:
        con.close()
    return [
        LookalikeCandidate(
            target_id=row[0],
            target_text=row[1],
            known_id=row[2],
            known_text=row[3],
            known_language=row[4],
            similarity=round(row[5], 4),
            kind=row[6],
            shares_concept=row[7],
            same_key=row[8],
            same_pos=row[9],
            form_similarity=round(row[10], 4),
            known_zipf=row[11],
        )
        for row in rows
        if row[4] in known
    ]


#: The candidate query. ``keyed`` is the registered table of keyed words;
#: parameters are the target language and the threshold. Best sense follows
#: `lemma_store`: highest sense frequency, then concept commonness, then band.
_CANDIDATE_SQL = """
WITH pairs AS (
  SELECT DISTINCT a.id AS tid, a.text AS ttext, b.id AS kid, b.text AS ktext,
         b.language AS klang, a.key = b.key AS same_key,
         coalesce(a.pos = b.pos, false) AS same_pos,
         1 - levenshtein(a.folded, b.folded)
             / greatest(length(a.folded), length(b.folded)) AS form_sim,
         greatest(
           1 - levenshtein(a.key, b.key) / greatest(length(a.key), length(b.key)),
           form_sim
         ) AS sim
  FROM keyed a JOIN keyed b
    ON a.language = $1 AND b.language <> $1
   AND (left(a.key, 2) = left(b.key, 2)
        OR (length(a.skel) >= 2 AND left(a.skel, 3) = left(b.skel, 3)))
   AND abs(length(a.key) - length(b.key)) <= greatest(2, length(a.key) // 3)
  WHERE length(a.key) >= 3 AND length(b.key) >= 3
),
cand AS (SELECT * FROM pairs WHERE sim >= $2),
ids AS (SELECT tid AS id FROM cand UNION SELECT kid FROM cand),
best AS (
  SELECT lemma_id, concept_id FROM (
    SELECT s.lemma_id, s.concept_id,
           row_number() OVER (
             PARTITION BY s.lemma_id
             ORDER BY s.sense_frequency DESC NULLS LAST,
                      c.commonness DESC NULLS LAST,
                      s.cefr_level ASC NULLS LAST, s.concept_id
           ) AS rank
    FROM {senses} s JOIN {concepts} c ON c.id = s.concept_id
    WHERE s.lemma_id IN (SELECT id FROM ids)
  ) WHERE rank = 1
),
lemma_senses AS (
  SELECT lemma_id, concept_id FROM {senses} WHERE lemma_id IN (SELECT id FROM ids)
),
members AS (
  SELECT s.concept_id, l.id AS lemma_id, l.language
  FROM {senses} s JOIN {lemmas} l ON l.id = s.lemma_id
  WHERE s.concept_id IN (SELECT concept_id FROM lemma_senses)
),
signals AS (
  SELECT c.*,
    EXISTS (SELECT 1 FROM best bt JOIN members m ON m.concept_id = bt.concept_id
            WHERE bt.lemma_id = c.tid AND m.lemma_id = c.kid)
    OR EXISTS (SELECT 1 FROM best bk JOIN members m ON m.concept_id = bk.concept_id
               WHERE bk.lemma_id = c.kid AND m.lemma_id = c.tid) AS main_shared,
    EXISTS (SELECT 1 FROM best bt JOIN best bk ON bt.concept_id = bk.concept_id
            WHERE bt.lemma_id = c.tid AND bk.lemma_id = c.kid) AS same_best,
    EXISTS (SELECT 1 FROM best bt JOIN members mt ON mt.concept_id = bt.concept_id
              AND mt.language = 'en'
            JOIN best bk ON bk.lemma_id = c.kid
            JOIN members mk ON mk.concept_id = bk.concept_id AND mk.language = 'en'
            JOIN {lemmas} lt ON lt.id = mt.lemma_id
            JOIN {lemmas} lk ON lk.id = mk.lemma_id
            WHERE bt.lemma_id = c.tid AND lt.normalized = lk.normalized) AS best_pivot,
    EXISTS (SELECT 1 FROM lemma_senses st JOIN lemma_senses sk
              ON st.concept_id = sk.concept_id
            WHERE st.lemma_id = c.tid AND sk.lemma_id = c.kid) AS any_shared,
    EXISTS (SELECT 1 FROM lemma_senses st
            JOIN members mt ON mt.concept_id = st.concept_id AND mt.language = 'en'
            JOIN lemma_senses sk ON sk.lemma_id = c.kid
            JOIN members mk ON mk.concept_id = sk.concept_id AND mk.language = 'en'
            JOIN {lemmas} lt ON lt.id = mt.lemma_id
            JOIN {lemmas} lk ON lk.id = mk.lemma_id
            WHERE st.lemma_id = c.tid AND lt.normalized = lk.normalized) AS any_pivot
  FROM cand c
)
SELECT tid, ttext, kid, ktext, klang, sim,
  CASE
    WHEN main_shared OR same_best OR (klang <> 'en' AND best_pivot) THEN 'cognate'
    WHEN any_shared OR (klang <> 'en' AND any_pivot) THEN 'partial'
    ELSE 'full'
  END AS kind,
  any_shared, same_key, same_pos, form_sim,
  (SELECT max(token_frequency) FROM {senses} z WHERE z.lemma_id = kid) AS kzipf
FROM signals
ORDER BY sim DESC, tid, kid
"""


#: Defaults of `select_candidates`, tuned on the gold set (phase 11 step 2).
DEFAULT_PER_TARGET = 2
DEFAULT_SELECT_THRESHOLD = 0.75
DEFAULT_MIN_KNOWN_ZIPF = 2.0


def rank_key(candidate: LookalikeCandidate) -> tuple[bool, bool, float, float, float]:
    """Return the sort key that puts a target lemma's best look-alike first.

    An identical cognate key beats a merely close one, a same-part-of-speech
    pair beats a derivational relative (pt *capitalista* / en *capitalism*),
    then similarity, then the closer spelling (keys are coarse on short words:
    pt *cola* keys like en *cola*, *cole* and *col*), then the more frequent
    known word, which the learner is likelier to know.
    """
    return (
        candidate.same_key,
        candidate.same_pos,
        candidate.similarity,
        candidate.form_similarity,
        candidate.known_zipf or 0.0,
    )


def select_candidates(
    candidates: Iterable[LookalikeCandidate],
    *,
    per_target: int = DEFAULT_PER_TARGET,
    threshold: float = DEFAULT_SELECT_THRESHOLD,
    min_known_zipf: float = DEFAULT_MIN_KNOWN_ZIPF,
) -> list[LookalikeCandidate]:
    """Keep each target lemma's best few look-alikes per known language.

    A trap only exists when the learner knows the look-alike, so the known side
    needs a token frequency of at least ``min_known_zipf`` (the target side is
    unrestricted: two rare words that look alike are still worth knowing).

    Args:
        candidates: Output of `find_candidates`.
        per_target: Look-alikes kept per (target lemma, known language).
        threshold: Minimum similarity.
        min_known_zipf: Minimum Zipf frequency of the known lemma.

    Returns:
        The kept candidates, best first within each target lemma.
    """
    groups: dict[tuple[str, str], list[LookalikeCandidate]] = {}
    for cand in candidates:
        if cand.similarity < threshold or (cand.known_zipf or 0.0) < min_known_zipf:
            continue
        groups.setdefault((cand.target_id, cand.known_language), []).append(cand)
    kept: list[LookalikeCandidate] = []
    for group in groups.values():
        group.sort(key=rank_key, reverse=True)
        kept.extend(group[:per_target])
    return kept


# --- Gold set -----------------------------------------------------------------

#: Committed hand-reviewed gold pairs, under ``data/curated/``.
GOLD_FILE = "lookalike_gold.jsonl"

#: A gold pair's kind: an edge kind, or ``noise`` (look-alike, not confusing).
GoldKind = Literal["full", "partial", "cognate", "noise"]

#: How a gold pair was chosen (see `GoldPair.origin`).
GoldOrigin = Literal["curated", "sampled-uniform", "sampled-close"]


class GoldPair(BaseModel):
    """One hand-reviewed look-alike pair of the gold set.

    Attributes:
        pair: ``"pt-en"`` or ``"pt-it"``.
        pt: The pt form.
        other_language: The other side's language.
        other: The other side's form.
        kind: The true kind, or ``noise``.
        reason: One line on why (the meanings involved).
        pt_lemma_id: The pt lemma's id.
        other_lemma_id: The other lemma's id.
        reviewed_by: ``"manual"`` for a hand-written row.
        origin: How the pair entered the set: ``curated`` (hand-picked known
            traps, cognates and coincidences; the base for generator recall),
            ``sampled-uniform`` (drawn at random from the selected candidates,
            so it measures precision on the real mix) or ``sampled-close``
            (drawn from the near-identical selected candidates, where the
            hard calls are).
    """

    pair: str
    pt: str
    other_language: str
    other: str
    kind: GoldKind
    reason: str
    pt_lemma_id: str
    other_lemma_id: str
    reviewed_by: str = "manual"
    origin: GoldOrigin = "curated"

    @property
    def ids(self) -> tuple[str, str]:
        """Return the unordered lemma-id pair."""
        a, b = sorted((self.pt_lemma_id, self.other_lemma_id))
        return a, b


def load_gold(data_fol: Path) -> list[GoldPair]:
    """Read the committed gold set (empty when the file does not exist)."""
    path = data_fol / CURATED_SUBDIR / GOLD_FILE
    return read_jsonl(GoldPair, path) if path.exists() else []


class GoldScore(BaseModel):
    """How a candidate set does against the gold set.

    Attributes:
        candidates: Candidates scored.
        found: Gold kind -> how many of its pairs are candidates.
        totals: Gold kind -> how many pairs the gold set has.
        kind_agreement: ``(gold kind, provisional kind)`` -> count, over the
            gold pairs that were found.
    """

    candidates: int
    found: dict[str, int]
    totals: dict[str, int]
    kind_agreement: dict[str, int]

    def recall(self, kind: str) -> float:
        """Return the share of a gold kind's pairs found (0 when it has none)."""
        total = self.totals.get(kind, 0)
        return self.found.get(kind, 0) / total if total else 0.0


def score_against_gold(
    candidates: Sequence[LookalikeCandidate],
    gold: Sequence[GoldPair],
) -> GoldScore:
    """Score a candidate set against the gold pairs.

    Recall is per gold kind. ``noise`` recall is the share of coincidental
    look-alikes that got through, so lower is better there; the verifier is what
    removes them.

    Args:
        candidates: The candidates to score.
        gold: The gold pairs.

    Returns:
        The score.
    """
    by_pair = {cand.pair: cand for cand in candidates}
    found: dict[str, int] = {}
    totals: dict[str, int] = {}
    agreement: dict[str, int] = {}
    for pair in gold:
        totals[pair.kind] = totals.get(pair.kind, 0) + 1
        cand = by_pair.get(pair.ids)
        if cand is None:
            continue
        found[pair.kind] = found.get(pair.kind, 0) + 1
        label = f"{pair.kind}->{cand.kind}"
        agreement[label] = agreement.get(label, 0) + 1
    return GoldScore(
        candidates=len(candidates),
        found=found,
        totals=totals,
        kind_agreement=agreement,
    )


# --- Verification worklist and proposals ----------------------------------------

#: English names of the languages the verifier prompt mentions.
LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "pt": "Portuguese",
    "it": "Italian",
    "es": "Spanish",
    "fr": "French",
}

#: Pairs per verifier request; instructions are paid once per chunk.
VERIFY_CHUNK_SIZE = 20

#: Senses shown per word, most common first.
_SENSES_SHOWN = 3

#: Committed curated look-alike edges (the verifier's reviewed output).
LOOKALIKES_FILE = "lookalikes.jsonl"


def sense_summary(store: LexiconStore, lemma_id: str) -> str:
    """Return a word's main senses as ``"gloss (English words)"`` strings.

    Args:
        store: The lexicon store.
        lemma_id: The lemma to summarize.

    Returns:
        Up to three senses, most common first, joined with `` / ``.
    """
    parts: list[str] = []
    for card in store.lemma_sense_cards(lemma_id)[:_SENSES_SHOWN]:
        english = ", ".join(card.translations.get("en", [])[:3])
        gloss = card.gloss or ""
        parts.append(f"{gloss} ({english})" if english else gloss)
    return " / ".join(part for part in parts if part)


def verify_chunks(
    store: LexiconStore,
    candidates: Sequence[LookalikeCandidate],
    *,
    target: str = "pt",
    size: int = VERIFY_CHUNK_SIZE,
) -> list[tuple[str, LookalikeVerifyInput]]:
    """Group candidates into verifier requests, one known language per chunk.

    Args:
        store: The lexicon store, for the sense summaries.
        candidates: The candidates to verify.
        target: The language being learned.
        size: Pairs per request.

    Returns:
        ``(chunk_key, input)`` pairs, deterministic for a given candidate set.
    """
    by_language: dict[str, list[LookalikeCandidate]] = {}
    for cand in sorted(candidates, key=lambda c: (c.known_language, c.key)):
        by_language.setdefault(cand.known_language, []).append(cand)
    summaries: dict[str, str] = {}

    def _senses(lemma_id: str) -> str:
        if lemma_id not in summaries:
            summaries[lemma_id] = sense_summary(store, lemma_id)
        return summaries[lemma_id]

    chunks: list[tuple[str, LookalikeVerifyInput]] = []
    for language, group in by_language.items():
        for start in range(0, len(group), size):
            part = group[start : start + size]
            chunks.append(
                (
                    f"{target}-{language}:{part[0].key}",
                    LookalikeVerifyInput(
                        target_language_name=LANGUAGE_NAMES[target],
                        known_language_name=LANGUAGE_NAMES[language],
                        pairs=[
                            PairSource(
                                key=cand.key,
                                target_word=cand.target_text,
                                target_senses=_senses(cand.target_id),
                                known_word=cand.known_text,
                                known_senses=_senses(cand.known_id),
                            )
                            for cand in part
                        ],
                    ),
                ),
            )
    return chunks


class LookalikeProposal(BaseModel):
    """One reviewable look-alike edge (a line of ``data/curated/lookalikes.jsonl``).

    Attributes:
        target_id: Lemma id on the learned side.
        target_text: Its form (review aid).
        known_id: Lemma id on the known side.
        known_text: Its form (review aid).
        known_language: The known side's language.
        kind: The verifier's verdict (``unrelated`` rows are kept as rejected).
        note: The learner note in English, for a false friend.
        similarity: The generator's similarity score.
        status: ``proposed`` until a reviewed run is accepted; only
            ``accepted`` rows are applied.
        model: Who produced the verdict: ``manual`` for a hand-written row,
            `REVIEW_MODEL` for an agent-reviewed batch (`lookalike_review`),
            otherwise the LLM verifier's model name.
        prompt_sha: The prompt's (or the review guide's) hash, for provenance.
        batch: The review batch the row came from (empty for other sources).
        edge_case: The reviewer flagged the call as a judgement call worth a
            second look; the row is applied all the same.
    """

    target_id: str
    target_text: str
    known_id: str
    known_text: str
    known_language: str
    kind: Literal["full", "partial", "cognate", "unrelated"]
    note: str = ""
    similarity: float | None = None
    status: Literal["proposed", "accepted", "rejected"] = "proposed"
    model: str = ""
    prompt_sha: str = ""
    batch: str = ""
    edge_case: bool = False


#: `LookalikeProposal.model` for rows reviewed in an agent-harness batch.
REVIEW_MODEL = "agent-review"


def proposal_source(row: LookalikeProposal) -> str:
    """Return the provenance tag of a row's edge: ``manual``, ``agent`` or ``llm``."""
    if row.model == "manual":
        return "manual"
    return "agent" if row.model == REVIEW_MODEL else "llm"


def near_identical(a: str, b: str) -> bool:
    """Return True when two forms differ only by accents, doubles or a final vowel.

    Such forms look the same to a reader whatever their origin (pt *data* / en
    *data*, pt *pato* / it *patto*), so a meaning difference is a trap even
    without a shared root.
    """

    def _bare(text: str) -> str:
        folded = _DOUBLE.sub(r"\1", fold(text))
        stripped = _FINAL_VOWELS.sub("", folded)
        return stripped if len(stripped) >= _MIN_KEY else folded

    return _bare(a) == _bare(b)


def is_trap(
    kind: str,
    *,
    same_root: bool | None,
    target_text: str,
    known_text: str,
) -> bool:
    """Decide whether a false-friend verdict stands (phase 11, prompt v5).

    A learner trap is a pair that shares a root whose meaning drifted, or a pair
    spelled (nearly) the same. A model asked for kinds alone over-calls mid
    resemblances (pt *castigo* / en *casting*); its etymology answer is the
    sharper signal, so a ``full`` / ``partial`` verdict without a shared root
    stands only for near-identical forms. A missing ``same_root`` (an older
    prompt) keeps the verdict.

    Args:
        kind: The verdict.
        same_root: The model's etymology answer.
        target_text: The learned-side form.
        known_text: The known-side form.

    Returns:
        True when the pair is kept as a false friend.
    """
    if kind not in {"full", "partial"}:
        return False
    return same_root is not False or near_identical(target_text, known_text)


def proposals_from_verdicts(
    candidates: Sequence[LookalikeCandidate],
    outputs: Iterable[LookalikeVerifyOutput],
    *,
    model: str = "",
    prompt_sha: str = "",
) -> list[LookalikeProposal]:
    """Turn verifier outputs into reviewable proposals.

    A verdict whose key matches no candidate is dropped (the model mistyped
    it). A false-friend verdict that fails `is_trap` becomes ``unrelated``. An
    ``unrelated`` verdict, or a false friend without a note, is written as
    ``rejected`` so the review sees it but the build never applies it.

    Args:
        candidates: The candidates that were verified.
        outputs: The verifier outputs.
        model: The model name, recorded on each row.
        prompt_sha: The prompt hash, recorded on each row.

    Returns:
        One proposal per matched verdict, sorted by key.
    """
    by_key = {cand.key: cand for cand in candidates}
    rows: dict[str, LookalikeProposal] = {}
    for output in outputs:
        for verdict in output.verdicts:
            cand = by_key.get(verdict.key)
            if cand is None:
                continue
            note = " ".join(verdict.note.split())
            kind = verdict.kind
            if kind in {"full", "partial"} and not is_trap(
                kind,
                same_root=verdict.same_root,
                target_text=cand.target_text,
                known_text=cand.known_text,
            ):
                kind = "unrelated"
            missing_note = kind in {"full", "partial"} and not note
            rows[cand.key] = LookalikeProposal(
                target_id=cand.target_id,
                target_text=cand.target_text,
                known_id=cand.known_id,
                known_text=cand.known_text,
                known_language=cand.known_language,
                kind=kind,
                note=note if kind in {"full", "partial"} else "",
                similarity=cand.similarity,
                status=(
                    "rejected" if kind == "unrelated" or missing_note else "proposed"
                ),
                model=model,
                prompt_sha=prompt_sha,
            )
    return [rows[key] for key in sorted(rows)]


def accept_run(
    proposals: Sequence[LookalikeProposal],
    *,
    languages: Iterable[str],
) -> list[LookalikeProposal]:
    """Flip the ``proposed`` rows of the reviewed languages to ``accepted``."""
    chosen = set(languages)
    return [
        row.model_copy(update={"status": "accepted"})
        if row.status == "proposed" and row.known_language in chosen
        else row
        for row in proposals
    ]


def load_lookalikes(data_fol: Path) -> list[LookalikeProposal]:
    """Read the accepted rows of the committed look-alike file, if any.

    A pair can have several rows when it was re-checked; only its latest row
    counts, so a later ``unrelated`` (rejected) row retracts an earlier edge.
    """
    path = curated_path(data_fol, LOOKALIKES_FILE)
    if not path.exists():
        return []
    latest: dict[tuple[str, str], LookalikeProposal] = {}
    for row in read_jsonl(LookalikeProposal, path):
        latest.pop((row.target_id, row.known_id), None)
        latest[row.target_id, row.known_id] = row
    return [row for row in latest.values() if row.status == "accepted"]


#: A trap (``full`` / ``partial``) needs its known word at least this frequent
#: (Zipf); a learner is unlikely to know a rarer one (en *palaver*, *bonito*),
#: so it misleads nobody.
MIN_TRAP_KNOWN_ZIPF = 3.3


def drop_rare_traps(
    proposals: Iterable[LookalikeProposal],
    zipf: Callable[[str, str], float],
    min_zipf: float = MIN_TRAP_KNOWN_ZIPF,
) -> tuple[list[LookalikeProposal], int]:
    """Drop the traps whose known word is too rare to mislead a learner.

    Cognate rows are kept whatever the frequency. Pass the latest row per pair
    (`load_lookalikes`), so dropping a row never lets an older one through.

    Args:
        proposals: The rows to filter.
        zipf: ``(text, language) -> Zipf frequency``, e.g.
            `sources.frequency.token_zipf`.
        min_zipf: Lowest Zipf frequency of a trap's known word.

    Returns:
        ``(kept rows, traps dropped)``.
    """
    kept: list[LookalikeProposal] = []
    dropped = 0
    for row in proposals:
        if row.kind in {"full", "partial"} and (
            zipf(row.known_text, row.known_language) < min_zipf
        ):
            dropped += 1
            continue
        kept.append(row)
    if dropped:
        lg.info("Look-alikes: {} trap(s) with a rare known word dropped", dropped)
    return kept, dropped


def apply_lookalikes(
    lemma_ids: Iterable[str],
    proposals: Iterable[LookalikeProposal],
) -> tuple[list[LookalikeRelation], list[str], int]:
    """Build the look-alike edges from accepted proposals (phase 11).

    A row whose lemmas are not both in the build is counted as stale and
    skipped, never fatal (the curated-input rule). ``unrelated`` rows never
    become edges, and retract an earlier row's edge for the same pair.

    Args:
        lemma_ids: Every lemma id of the build.
        proposals: Accepted rows, typically from `load_lookalikes`.

    Returns:
        ``(edges, sources, stale)``: one edge per pair (a later row for the
        same pair wins), its provenance tag (`proposal_source`), and the
        stale row count.
    """
    known = set(lemma_ids)
    edges: dict[tuple[str, str], tuple[LookalikeRelation, str]] = {}
    stale = 0
    for row in proposals:
        if row.kind == "unrelated":
            edges.pop((row.target_id, row.known_id), None)
            continue
        if row.target_id not in known or row.known_id not in known:
            stale += 1
            continue
        notes = {"en": row.note} if row.note else {}
        edge = LookalikeRelation(
            lemma_id_a=row.target_id,
            lemma_id_b=row.known_id,
            kind=row.kind,
            similarity_score=row.similarity,
            explanation_notes=notes,
        )
        source = proposal_source(row)
        edges[edge.lemma_id_a, edge.lemma_id_b] = (edge, source)
    if stale:
        lg.warning("Look-alikes: {} stale row(s) skipped", stale)
    ordered = [edges[pair] for pair in sorted(edges)]
    return [edge for edge, _ in ordered], [source for _, source in ordered], stale
