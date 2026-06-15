# Concept model - brainstorm spec

Status: brainstorm / design exploration. Not implemented yet.

This spec consolidates the raw dump in `00-concepts-brainstorm-dump.md` into a
single design proposal, cross-referenced against the existing `lang_tools.words`
code and the linux-box `10-language-overview` design notes, and grounded in
standard lexical-resource modelling (WordNet, OntoLex-Lemon, BabelNet).

## Motivation

Today a `Word` in `lang_tools.words.word` is a single flat lexical entry that
mixes three different kinds of information:

- the **lexical token** itself (`text`, `language`, `normalized`, `part_of_speech`),
- its **meanings** (`glosses`, `translations`), and
- **cross-lingual relationships** (`false_friends`, embedded directly on the word).

This works for vocab lists but breaks down once we want to model meaning
properly:

- **Polysemy** - one token ("banco") has several unrelated meanings. A flat
  word cannot say "this string means A *or* B".
- **Synonymy / dialect** - several tokens in one language ("trem" / "comboio")
  share one meaning. There is no shared node to hang them on.
- **Cognates** - tokens across languages share a meaning ("university" /
  "universidade" / "universidad"). Right now the only link is a `translations`
  dict, which is pairwise and lossy.
- **False friends** - the current `false_friends: list[FalseFriend]` lives on the
  word, so the link must be added symmetrically by hand on both words, which is a
  data-integrity hazard.

The fix is a **concept-centric architecture**: keep `Word` as a thin lexical
token and introduce a language-independent `Concept` (a synset) that owns
meaning. Words point at concepts; concepts gather words.

## Background: how lexical resources model this

The split we want is the standard one in computational lexicography. Terminology
we borrow:

- **Lemma / lexical entry** - the canonical surface token in one language. This
  is our `Word`.
- **Sense** - a lemma disambiguated to one meaning; a lemma with N meanings has
  N senses. This is the `word -> concept` link (polysemy lives here).
- **Synset / lexical concept** - a language-independent meaning that several
  lemmas (within and across languages) can realise. This is our `Concept`.
- **Gloss** - the definition text of a sense / concept, optionally with
  examples.

WordNet groups synonymous lemmas into **synsets** and treats the synset as the
unit of meaning. BabelNet extends the synset to hold lexicalizations in 250+
languages under one stable cross-lingual id - exactly the multilingual concept
node we want. OntoLex-Lemon formalises the same layering (lexical entry ->
lexical sense -> lexical concept) and the principle of *semantics by reference*:
a token's meaning is expressed by pointing at a shared concept, not by inlining
it. See References.

## Proposed models

### `Word` (lexical token, thin)

Keep the existing token-level fields, and add a link to the meanings it can
carry. Heavy relationship data moves off the word.

```python
class Word(BaseModel):
    """A purely lexical token in one language."""
    text: str
    language: str
    normalized: str = ""
    part_of_speech: str | None = None

    # links this token to its meanings (this edge is where polysemy lives)
    concept_ids: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def id(self) -> str:
        """Deterministic id derived from (text, language)."""
        return word_id(self.text, self.language)
```

### `Concept` (language-independent meaning / synset)

```python
class Concept(BaseModel):
    """A language-independent semantic meaning (a synset)."""
    id: str                                          # e.g. "c_library_place"
    definitions: dict[str, str] = Field(default_factory=dict)  # {"en": "...", "pt": "..."}
    lemmas: dict[str, list[str]] = Field(default_factory=dict)  # {"en": ["w_library_en"], "pt": [...]}
```

- `definitions` is the per-language gloss of the concept.
- `lemmas` lists, per language, the word ids that realise this concept.
- A concept with `len(lemmas[lang]) > 1` is a synonym/dialect group in that
  language.
- A concept with multiple language keys is an implicit cognate/translation set.

### `FalseFriendRelation` (decoupled edge table)

False friends are a relationship between two tokens that look alike but mean
different things, so they belong to **different** concepts. Model the link as a
standalone edge rather than a field on `Word`.

```python
class FalseFriendRelation(BaseModel):
    """A symmetrical false-friend edge between two word ids."""
    word_id_a: str
    word_id_b: str
    similarity_score: float | None = None
    # per-language learner notes
    explanation_notes: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _enforce_deterministic_order(self) -> FalseFriendRelation:
        """Canonical orientation: word_id_a < word_id_b, so the pair is unique."""
        if self.word_id_a > self.word_id_b:
            self.word_id_a, self.word_id_b = self.word_id_b, self.word_id_a
        return self
```

Canonical ordering (`word_id_a < word_id_b`) guarantees each symmetric pair is
stored once and dedups cleanly on ingestion.

## The four phenomena, by example

### 1. Polysemy - one token, many concepts

"banco" (pt) is both a financial institution and a bench. The token exists once
and points at two concepts.

```python
word_banco_pt = Word(text="banco", language="pt",
                     concept_ids=["c_financial_bank", "c_seating_bench"])

concept_financial_bank = Concept(
    id="c_financial_bank",
    definitions={"pt": "Instituicao que aceita depositos e realiza emprestimos.",
                 "en": "A financial institution licensed to take deposits and make loans."},
    lemmas={"pt": ["w_banco_pt"], "en": ["w_bank_en"]},
)
concept_seating_bench = Concept(
    id="c_seating_bench",
    definitions={"pt": "Assento longo para varias pessoas, comum em parques.",
                 "en": "A long seat for several people, typically in parks."},
    lemmas={"pt": ["w_banco_pt"], "en": ["w_bench_en"]},
)
```

### 2. Synonymy / dialect - one concept, many lemmas in a language

"trem" (BR) and "comboio" (PT) are the same thing. The concept holds both under
the `pt` key.

```python
concept_railway_train = Concept(
    id="c_railway_train",
    definitions={"en": "A series of railway carriages moved by a locomotive.",
                 "pt": "Meio de transporte que se desloca sobre trilhos."},
    lemmas={"en": ["w_train_en"], "pt": ["w_trem_pt", "w_comboio_pt"]},
)
word_trem_pt = Word(text="trem", language="pt", concept_ids=["c_railway_train"])
word_comboio_pt = Word(text="comboio", language="pt", concept_ids=["c_railway_train"])
```

### 3. Cognates / real friends - implicit cross-lingual links

Cognates share history and meaning. No explicit edge is needed: they sit under
one concept node, the same way BabelNet gathers cross-lingual lexicalizations of
one synset.

```python
concept_university = Concept(
    id="c_university_institution",
    definitions={"en": "An institution of higher learning that awards degrees.",
                 "pt": "Instituicao de ensino superior que concede graus.",
                 "es": "Institucion de ensenanza superior que otorga titulos."},
    lemmas={"en": ["w_university_en"], "pt": ["w_universidade_pt"], "es": ["w_universidad_es"]},
)
```

The app layer can run a string-similarity check (e.g. Levenshtein) across the
lemmas of one concept to auto-flag the close ones as "real friends".

### 4. False friends - separate concepts plus an edge

"embarazada" (es, *pregnant*) vs "embarrassed" (en). The meanings conflict, so
they are separate concepts; the deceptive resemblance is recorded as an edge.

```python
# distinct concepts
concept_pregnant = Concept(id="c_pregnant_state", ...)
concept_embarrassed = Concept(id="c_feeling_embarrassed", ...)

# global edge table, stored out of band (false_friends.json / .csv)
false_friends_db = [
    FalseFriendRelation(
        word_id_a="w_embarrassed_en",
        word_id_b="w_embarazada_es",
        similarity_score=0.88,
        explanation_notes={
            "en": "Spanish 'embarazada' means 'pregnant'. For humiliated use 'avergonzado'.",
            "es": "Ingles 'embarrassed' significa 'avergonzado'. Para gestacion usa 'pregnant'.",
        },
    ),
]
```

## Storage and indexing

The existing `word_store.py` is an in-memory, read-only store loaded from
bootstrap CSVs at import time (`_ALL_WORDS`, `_BY_ID`). Extend it with concept
and false-friend registries plus a symmetric look-aside index.

```python
_ALL_FALSE_FRIENDS: list[FalseFriendRelation] = _load_false_friends()
_FALSE_FRIENDS_BY_WORD_ID: dict[str, list[FalseFriendRelation]] = defaultdict(list)

def _index_false_friends() -> None:
    for rel in _ALL_FALSE_FRIENDS:
        _FALSE_FRIENDS_BY_WORD_ID[rel.word_id_a].append(rel)
        _FALSE_FRIENDS_BY_WORD_ID[rel.word_id_b].append(rel)

def get_false_friends_for_word(word_id: str) -> list[tuple[Word, FalseFriendRelation]]:
    """Return each false friend of a word as (other_word, edge)."""
    out: list[tuple[Word, FalseFriendRelation]] = []
    for rel in _FALSE_FRIENDS_BY_WORD_ID.get(word_id, []):
        other_id = rel.word_id_b if rel.word_id_a == word_id else rel.word_id_a
        other = _BY_ID.get(other_id)
        if other is not None:
            out.append((other, rel))
    return out
```

Analogous concept indexes: `_CONCEPTS_BY_ID`, plus `concepts_for_word(word_id)`
and `words_for_concept(concept_id, language=None)`.

### Why the edge table over embedded `false_friends`

- **Lean payloads** - `GET /api/v1/words/{id}` returns a clean token; heavy
  relationship graphs are fetched only when building a vocabulary-trap exercise.
- **Single-row ingestion** - a CSV/LLM loader appends one row to
  `false_friends.csv` instead of fetching, editing, and re-saving two word rows.
- **No symmetry bugs** - the canonical ordering means the link cannot be added on
  one side and forgotten on the other.
- **Reusable** - the same pattern fits any explicit token-to-token edge (e.g.
  irregular cognate pairs that do not share one clean concept).

## What we want to do with the concept model

Grounding from `lang-tutor` exercises and the `03-exercise-framework` notes:

- **Synonym / dialect drills** - pick a `Concept` whose `lemmas[lang]` has more
  than one entry. Feeds a pair-matching variant ("trem" = "comboio") and lets the
  tutor teach BR vs PT register.
- **Word-to-definition pair matching** - the framework already lists a
  word-to-definition variant of `pair_matching`; concept `definitions` are the
  natural source of the gloss side.
- **Cognate flashcard decks** - gather a concept's cross-lingual lemmas and rank
  by string similarity to surface "free" vocabulary for the learner.
- **False-friend warnings / trap exercises** - on word selection, hit
  `_FALSE_FRIENDS_BY_WORD_ID`; if an edge exists, show the `explanation_notes` in
  the learner's language as a warning or quiz distractor.
- **Better translation lookups** - `pair_matching` currently relies on
  `Word.translations[target]` and raises `MissingTranslationError` when absent.
  Concepts can supply translations transitively (token -> concept ->
  lemmas[target]), filling gaps that the flat `translations` dict misses.
- **Disambiguation in the conversational tutor** - when the LLM flags a word the
  user misused, the concept link lets us point at the *intended* sense rather
  than the surface string.

## Bootstrap source

Decision: **OMW as the concept backbone, Wiktionary for enrichment, LLM only for
mapping.** Scoped to the ecosystem's target languages (pt, fr, es, it, en).

### Open Multilingual Wordnet (OMW) - the concept source

OMW is the cleanest fit because its core unit *is* the concept we want:

- **Synsets = `Concept`.** OMW synsets are already language-independent meanings,
  linked across languages through the Princeton WordNet interlingual index (ILI).
  That gives cross-lingual cognate grouping for free - the BabelNet-style shared
  sense inventory this spec describes.
- **Covers all five target languages** (pt, fr, es, it, en are all present).
- **Apache-2.0 licensed** - permissive, no share-alike obligation, safe to ship
  in bootstrap data.
- **First-class Python access** via the `wn` library (`pip install wn`): it
  downloads wordnets, queries synsets, and traverses the ILI. Maps almost
  directly onto `Concept`: id = ILI / synset key, `definitions` = synset gloss
  per language, `lemmas` = synset members per language.

### Wiktionary (wiktextract / kaikki.org) - enrichment layer

OMW gloss and example coverage is uneven across non-English languages. Kaikki
publishes per-language JSONL with rich glosses, example sentences, and
translations; pull these to fill `definitions` and example fields. Caveats:

- Wiktionary is **CC-BY-SA (share-alike)** - viral license, keep it isolated to
  an enrichment layer rather than the concept core.
- It is **lemma-centric with no shared concept ids**, so key it by lemma and join
  onto OMW synsets; do not treat it as the concept source.

### LLM - mapping only, not a data source

The hard part is linking the *existing* flat bootstrap word list onto OMW synsets
and collapsing WordNet's fine-grained senses into learner-appropriate
granularity. That is where an LLM earns its keep (and is verifiable against OMW),
rather than hallucinating definitions from scratch.

### Why not the alternatives as primary source

- **Wiktionary alone** - no cross-lingual concept ids (you would rebuild synset
  clustering yourself) and a viral license.
- **LLM alone** - no ground truth, token cost, and needs validation against
  something, which would be OMW anyway.

### First slice

1. `pip install wn`, download `omw` for en/pt/es/fr/it.
2. Export synsets to `data/bootstrap/concepts.csv` (concept id = ILI key,
   `definitions`, `lemmas`).
3. LLM-match the current bootstrap words onto synset ids to populate
   `Word.concept_ids`.
4. Enrich sparse glosses/examples from kaikki where needed.

Sources: [Open Multilingual Wordnet](https://omwn.org/),
[`wn` PyPI](https://pypi.org/project/wn/) /
[goodmami/wn](https://github.com/goodmami/wn),
[OMW Portuguese license](https://github.com/omwn/omw-data/blob/main/wns/por/LICENSE),
[wiktextract](https://github.com/tatuylonen/wiktextract) /
[kaikki.org](https://kaikki.org/dictionary/index.html).

## Relationship to existing code and migration notes

- `Word` already carries `glosses`, `translations`, `false_friends`,
  `examples`, and several computed fields (`has_accent`, `accented_chars`,
  `length`). The concept model does not replace those overnight.
- Migration path: introduce `Concept` and `concept_ids` additively; keep
  `translations` and embedded `false_friends` working; backfill concepts from
  existing data; then deprecate embedded `false_friends` in favour of the edge
  table once the indexes are in place.
- `word_id` (sha1 of `language::normalized`, 16 hex chars) already gives stable
  ids for dedup; concept ids should get a parallel deterministic scheme (the dump
  uses readable slugs like `c_library_place`; decide slug vs hash - see open
  questions).
- The `02-shared-data-layer` open question on glosses ("per-sense vs flattened")
  is answered by this model: a sense maps to a concept, and the concept owns the
  gloss.

## Open questions

- **Concept ids: readable slug vs hash?** Slugs (`c_seating_bench`) are
  debuggable but need a uniqueness discipline and a curation process; hashes are
  collision-safe but opaque and need a stable seed (what is a concept's natural
  key - its English gloss? a WordNet synset id?).
- **Bootstrap source.** Decided - see the "Bootstrap source" section above (OMW
  via `wn` as the concept backbone, Wiktionary for enrichment, LLM for mapping).
- **Do glosses stay on `Word` too, or move entirely to `Concept`?** Leaning:
  concept owns canonical glosses; word may keep raw Wiktionary glosses as
  provenance until backfill is complete.
- **Storage format.** Concepts and false-friend edges as new CSVs in
  `data/bootstrap/`, or graduate to a small DB once the graph grows? CSV keeps
  the current import-time in-memory model; a graph/relational store scales the
  relationship queries.
- **Relations beyond false friends.** Do we model hypernymy / hyponymy (WordNet's
  is-a backbone) and antonymy, or keep the concept layer flat (just sense
  grouping) for now?
- **Concept granularity.** How fine do senses get? WordNet is famously
  fine-grained; for a learner app a coarser inventory is usually better.

## References

- WordNet (Princeton) - synsets, lemmas, senses, hypernymy backbone:
  [senseidx(5WN)](https://wordnet.princeton.edu/documentation/senseidx5wn),
  [overview](https://medium.com/@jolalf/wordnet-lexical-database-grouped-into-synsets-case-study-e059f66e847b)
- BabelNet - multilingual synset, cross-lingual stable sense inventory:
  [About BabelNet](https://babelnet.org/about),
  [Ten Years of BabelNet survey](https://www.ijcai.org/proceedings/2021/0620.pdf)
- OntoLex-Lemon - lexical entry / sense / lexical concept, semantics by
  reference: [OntoLex (Wikipedia)](https://en.wikipedia.org/wiki/OntoLex),
  [Lexicon Model for Ontologies draft](https://www.w3.org/2016/04/ontolex/),
  [McCrae et al., OntoLex-Lemon model](https://john.mccr.ae/papers/mccrae2017ontolex.pdf)
- Internal: `lang_tools/words/word.py`, `word_store.py`, `word_id.py`;
  `linux-box-cloudflare/scratch_space/vibes/10-language-overview/`
  (`02-shared-data-layer.md`, `03-exercise-framework.md`).
