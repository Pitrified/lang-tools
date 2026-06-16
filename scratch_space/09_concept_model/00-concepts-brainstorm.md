# Concept model - brainstorm spec

Status: brainstorm / design exploration. Not implemented yet.

This spec consolidates the raw dump in `00-concepts-brainstorm-dump.md` into a
single design proposal, cross-referenced against the existing `lang_tools.lexicon`
code and the linux-box `10-language-overview` design notes, and grounded in
standard lexical-resource modelling (WordNet, OntoLex-Lemon, BabelNet).

Naming note: the core lexical-token class is `Lemma` (renamed from `Word`; see
"Naming: `Lemma`, not `Word`" and phase 1 in `tracking.md`). This spec uses
`Lemma` throughout.

## Motivation

Today a `Lemma` (the flat class, renamed from `Word` in phase 1) in
`lang_tools.lexicon.lemma` is a single flat lexical entry that mixes three
different kinds of information:

- the **lexical token** itself (`text`, `language`, `normalized`, `part_of_speech`),
- its **meanings** (`glosses`, `translations`), and
- **cross-lingual relationships** (`false_friends`, embedded directly on the lemma).

This works for vocab lists but breaks down once we want to model meaning
properly:

- **Polysemy** - one token ("banco") has several unrelated meanings. A flat
  lemma cannot say "this string means A *or* B".
- **Synonymy / dialect** - several tokens in one language ("trem" / "comboio")
  share one meaning. There is no shared node to hang them on.
- **Cognates** - tokens across languages share a meaning ("university" /
  "universidade" / "universidad"). Right now the only link is a `translations`
  dict, which is pairwise and lossy.
- **False friends** - the current `false_friends: list[FalseFriend]` lives on the
  lemma, so the link must be added symmetrically by hand on both lemmas, which is
  a data-integrity hazard.

The fix is a **concept-centric architecture**: keep `Lemma` as a thin lexical
token and introduce a language-independent `Concept` (a synset) that owns
meaning. Lemmas point at concepts; concepts gather lemmas.

## Background: how lexical resources model this

The split we want is the standard one in computational lexicography. Terminology
we borrow:

- **Lemma / lexical entry** - the canonical surface token in one language. This
  is our `Lemma`.
- **Sense** - a lemma disambiguated to one meaning; a lemma with N meanings has
  N senses. This is the `lemma -> concept` link (polysemy lives here).
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

### `Lemma` (lexical token, thin)

Keep the existing token-level fields, and add a link to the meanings it can
carry. Heavy relationship data moves off the lemma.

```python
class Lemma(BaseModel):
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
        return lemma_id(self.text, self.language)
```

> **Decided (phase 2): `concept_ids` is dropped from `Lemma`.** The explicit
> `Sense` edge (see "Modeling implication" below) is the single source of truth for
> lemma <-> concept membership, so the persisted `Lemma` carries no `concept_ids`
> list. Callers reach a lemma's meanings through the hydrated `lemma.senses` /
> `lemma.concepts` representation view (phase 4). The `concept_ids` field shown
> above is the original sketch; it is superseded.

#### Naming: `Lemma`, not `Word`

Decided (green-lit): the class is `Lemma`, not `Word`. The literature term for
"a canonical surface token in one language" is **lemma** (used by WordNet,
OntoLex-Lemon, BabelNet - see Background). Because the model is being reshaped
anyway and the only consumer is ours, we rename `Word -> Lemma` (and
`word_id -> lemma_id`, the `w_` id prefix -> `l_`, module `word.py -> lemma.py`,
`word_store.py -> lemma_store.py`, `word_id.py -> lemma_id.py`; `concept_ids`
stays). The package is renamed `lang_tools.words -> lang_tools.lexicon` rather
than `lemmas`, because it holds the whole lexical graph (`Lemma`, `Concept`,
`Sense`, relation edges), not lemmas alone. Tracked as the preliminary phase 1 so
every later phase is written in the target vocabulary.

Why (the rationale, for the record):

- **Matches the literature** the whole design is grounded in; the code reads the
  same as the spec and the references.
- **Disambiguates the layers** - `Lemma` / `Sense` / `Concept` are three distinct,
  well-understood terms; "word" is overloaded (token? entry? string?).
- **Costless drift later is avoided** - renaming now (at ~50 sample lemmas, one
  owned consumer) is far cheaper than after the dataset and APIs grow.

Costs accepted:

- **Large but mechanical refactor** - touches the lemma module, store, and id
  helper, every import, and `lang-tutor`. Wide diff, low risk.
- **"Lemma" is less obvious to casual readers** than "word"; mitigated by a
  one-line class docstring.
- Public/external surface (none today) would need an alias if that ever changes.

### `Concept` (language-independent meaning / synset)

```python
class Concept(BaseModel):
    """A language-independent semantic meaning (a synset)."""
    id: str                                          # e.g. "c_library_place"
    definitions: dict[str, str] = Field(default_factory=dict)  # {"en": "...", "pt": "..."}
    lemmas: dict[str, list[str]] = Field(default_factory=dict)  # {"en": ["l_library_en"], "pt": [...]}
```

- `definitions` is the per-language gloss of the concept.
- `lemmas` lists, per language, the lemma ids that realise this concept.
- A concept with `len(lemmas[lang]) > 1` is a synonym/dialect group in that
  language.
- A concept with multiple language keys is an implicit cognate/translation set.

> **Decided (phase 2): `lemmas` is dropped from the persisted `Concept`.** Once the
> explicit `Sense` edge exists (see below), per-language membership is fully
> derivable from the sense set (group a concept's senses, bucket by each lemma's
> language). Persisting `lemmas` too would duplicate the edge and risk one-sided
> drift - the same reason false friends are a decoupled edge. `Concept` is stored
> as `id` + `definitions` only; `concept.lemmas` (and the synonym-group /
> cognate-set reads above) return as a computed representation-layer view, hydrated
> by the store in phase 4, not a stored field. See
> [`02_core_models.md`](02_core_models.md), "Persistence vs representation".

### `FalseFriendRelation` (decoupled edge table)

False friends are a relationship between two tokens that look alike but mean
different things, so they belong to **different** concepts. Model the link as a
standalone edge rather than a field on `Lemma`.

```python
class FalseFriendRelation(BaseModel):
    """A symmetrical false-friend edge between two lemma ids."""
    lemma_id_a: str
    lemma_id_b: str
    similarity_score: float | None = None
    # per-language learner notes
    explanation_notes: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _enforce_deterministic_order(self) -> FalseFriendRelation:
        """Canonical orientation: lemma_id_a < lemma_id_b, so the pair is unique."""
        if self.lemma_id_a > self.lemma_id_b:
            self.lemma_id_a, self.lemma_id_b = self.lemma_id_b, self.lemma_id_a
        return self
```

Canonical ordering (`lemma_id_a < lemma_id_b`) guarantees each symmetric pair is
stored once and dedups cleanly on ingestion.

## The four phenomena, by example

### 1. Polysemy - one token, many concepts

"banco" (pt) is both a financial institution and a bench. The token exists once
and points at two concepts.

```python
lemma_banco_pt = Lemma(text="banco", language="pt",
                       concept_ids=["c_financial_bank", "c_seating_bench"])

concept_financial_bank = Concept(
    id="c_financial_bank",
    definitions={"pt": "Instituição que aceita depositos e realiza empréstimos.",
                 "en": "A financial institution licensed to take deposits and make loans."},
    lemmas={"pt": ["l_banco_pt"], "en": ["l_bank_en"]},
)
concept_seating_bench = Concept(
    id="c_seating_bench",
    definitions={"pt": "Assento longo para varias pessoas, comum em parques.",
                 "en": "A long seat for several people, typically in parks."},
    lemmas={"pt": ["l_banco_pt"], "en": ["l_bench_en"]},
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
    lemmas={"en": ["l_train_en"], "pt": ["l_trem_pt", "l_comboio_pt"]},
)
lemma_trem_pt = Lemma(text="trem", language="pt", concept_ids=["c_railway_train"])
lemma_comboio_pt = Lemma(text="comboio", language="pt", concept_ids=["c_railway_train"])
```

### 3. Cognates / real friends - implicit cross-lingual links

Cognates share history and meaning. No explicit edge is needed: they sit under
one concept node, the same way BabelNet gathers cross-lingual lexicalizations of
one synset.

```python
concept_university = Concept(
    id="c_university_institution",
    definitions={"en": "An institution of higher learning that awards degrees.",
                 "pt": "Instituição de ensino superior que concede graus.",
                 "es": "Institucion de ensenanza superior que otorga titulos."},
    lemmas={"en": ["l_university_en"], "pt": ["l_universidade_pt"], "es": ["l_universidad_es"]},
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
        lemma_id_a="l_embarrassed_en",
        lemma_id_b="l_embarazada_es",
        similarity_score=0.88,
        explanation_notes={
            "en": "Spanish 'embarazada' means 'pregnant'. For embarrassed use 'avergonzado'.",
            "es": "Ingles 'embarrassed' significa 'avergonzado'. Para gestacion usa 'pregnant'.",
        },
    ),
]
```

## Lemma frequency

"How common is this lemma?" is a first-class signal for a learner app: it drives
vocabulary ordering (teach frequent lemmas first), difficulty grading, and
distractor selection. It is missing from the current model and needs designing
in deliberately because of a polysemy trap.

### The polysemy trap

Frequency is not a property of the surface token. "bank" is a very common English
lemma, but that count is dominated by the *financial* sense; the *river bank*
sense is comparatively rare. A single number on `Lemma` would conflate the two
and mislead any frequency-ordered drill. Frequency is therefore most correctly a
property of the **sense** - the `lemma -> concept` link - not of the bare token.

### Two granularities

- **Token frequency** - how often the surface form appears in a corpus,
  regardless of meaning. Cheap and widely available.
- **Sense frequency** - how often the form appears *in a given meaning*.
  Expensive: it needs a sense-tagged corpus, which is scarce outside English.

The pragmatic plan: always populate token frequency (easy), and populate sense
frequency where a source exists, otherwise approximate (e.g. split the token
frequency across senses using WordNet sense-tag counts as weights, or mark the
sense frequency as estimated).

### Modeling implication: an explicit sense edge

The brainstorm's current `Lemma.concept_ids: list[str]` makes the sense an
implicit, attribute-less edge. Carrying per-sense frequency (and later, per-sense
provenance or examples) pushes toward promoting that edge to an explicit object -
the OntoLex *lexical sense* made concrete:

```python
class Sense(BaseModel):
    """A lemma disambiguated to one concept; the lemma <-> concept edge."""
    lemma_id: str
    concept_id: str
    token_frequency: float | None = None   # zipf-scale, sense-independent (copy of Lemma's)
    sense_frequency: float | None = None    # zipf-scale for this meaning, may be estimated
    frequency_is_estimated: bool = False
    cefr_level: str | None = None            # "A1".."C2" for this meaning (see "Lemma complexity")
    cefr_is_estimated: bool = False

    @computed_field
    @property
    def id(self) -> str:
        return sense_id(self.lemma_id, self.concept_id)
```

Token frequency can also be cached on `Lemma` as a convenience aggregate (the max
across its senses), but the sense edge stays the source of truth.

> **Decided (phase 2): promote the explicit `Sense` edge now.** The richer
> per-sense metadata (frequency, CEFR, later provenance/examples) earns the
> dedicated object, and making `Sense` the canonical membership record lets both
> `Lemma.concept_ids` and `Concept.lemmas` drop (their membership is derivable from
> the sense set). `Sense` is the single place the lemma <-> concept relationship is
> stored. See [`02_core_models.md`](02_core_models.md).

### Sources

- **`wordfreq`** (MIT) - token frequency on the Zipf scale for many languages
  including all five targets; permissive license, ships well in an open dataset.
- **SUBTLEX / OpenSubtitles** frequency lists - subtitle-derived counts, good for
  spoken-register commonness; check per-list licensing before shipping.
- **WordNet sense-tag counts** (`tag_count`, from SemCor) - per-sense frequency
  ranking for English; the natural weight source for splitting token frequency
  across senses when no sense-tagged corpus exists for the target language.

## Lemma complexity (CEFR level)

Separate from "how common is it" is "how advanced is it": is this an **A1**
beginner word ("house", "eat") or a **C2** technical/abstract one
("photosynthesis", "notwithstanding")? A learner app uses this directly to grade
content, gate vocabulary by level, and pick distractors of comparable difficulty.
We use the **CEFR** scale (A1, A2, B1, B2, C1, C2) as the common vocabulary across
the ecosystem's languages.

### Related to frequency, but not the same

Complexity correlates with frequency - frequent lemmas tend to be easier - but the
two diverge often enough that complexity must be stored, not derived:

- Some **rare lemmas are conceptually simple** ("igloo" is rare but A2-easy).
- Some **frequent lemmas are advanced** in a given sense (abstract, idiomatic, or
  register-marked uses).

### Same polysemy trap, same home: the sense edge

Complexity is sense-dependent for exactly the reason frequency is. The basic
sense of "bank" (money) is A1; a figurative or technical sense can be B2/C1. So
CEFR level belongs on the **`Sense` edge**, right next to frequency, not on the
bare `Lemma`. This reinforces the "promote the sense edge" lean: frequency *and*
complexity are both per-sense signals that need a real edge object to live on
(`cefr_level`, `cefr_is_estimated` on `Sense`, see the model above).

A coarse lemma-level CEFR (the easiest sense's level) can be cached on `Lemma` as
a convenience aggregate, mirroring token frequency, but the sense edge stays the
source of truth.

### Sources

- **CEFR-graded word lists** - English Vocabulary Profile / Oxford 3000-5000 and
  the Kelly project lists (several languages) tag lemmas by CEFR band; join onto
  lemmas like the frequency lists. Licensing varies per list - check before
  shipping in an open dataset.
- **Estimation fallback** - where no graded list exists for a language, estimate
  from a blend of frequency band, lemma length/morphology, and an LLM judgment,
  and set `cefr_is_estimated = True`. Per-language CEFR sourcing is an open
  question (see below), parallel to sense-frequency sourcing.

## Storage and indexing

The store module (`lemma_store.py`, renamed from `word_store.py` in phase 1) is
an in-memory, read-only store loaded from bootstrap CSVs at import time
(`_ALL_LEMMAS`, `_LEMMAS_BY_ID`). Extend it with concept and false-friend
registries plus a symmetric look-aside index.

```python
_ALL_FALSE_FRIENDS: list[FalseFriendRelation] = _load_false_friends()
_FALSE_FRIENDS_BY_LEMMA_ID: dict[str, list[FalseFriendRelation]] = defaultdict(list)

def _index_false_friends() -> None:
    for rel in _ALL_FALSE_FRIENDS:
        _FALSE_FRIENDS_BY_LEMMA_ID[rel.lemma_id_a].append(rel)
        _FALSE_FRIENDS_BY_LEMMA_ID[rel.lemma_id_b].append(rel)

def get_false_friends_for_lemma(lemma_id: str) -> list[tuple[Lemma, FalseFriendRelation]]:
    """Return each false friend of a lemma as (other_lemma, edge)."""
    out: list[tuple[Lemma, FalseFriendRelation]] = []
    for rel in _FALSE_FRIENDS_BY_LEMMA_ID.get(lemma_id, []):
        other_id = rel.lemma_id_b if rel.lemma_id_a == lemma_id else rel.lemma_id_a
        other = _LEMMAS_BY_ID.get(other_id)
        if other is not None:
            out.append((other, rel))
    return out
```

Analogous concept indexes: `_CONCEPTS_BY_ID`, plus `concepts_for_lemma(lemma_id)`
and `lemmas_for_concept(concept_id, language=None)`.

> **Built (phase 4, refined in 4.1 / 4.2).** The store is now `LexiconStore`
> (`lang_tools.lexicon.lemma_store`): a **single indexed SQLite engine** built
> from the corpus on load, answering the full query surface above
> (`concept_relations_for` / `senses_for_*` included) with `SELECT`s. There is no
> resident/SQLite dual mode - the phase-4 resident dicts, eager `_hydrate()`,
> `LexiconStoreMode`, and `SqliteModeNotImplementedError` were removed in 4.1;
> back-refs are now filled **on demand** by `hydrate_lemma`/`hydrate_concept`/
> `hydrate_sense` (bounded 1-2 hops, fresh instances) and read through `resolve_*`
> accessors that raise `NotHydratedError` / `SenseNotHydratedError` when
> unhydrated. The on-disk format sits behind a Parquet codec seam (`codec.py`);
> `from_data_fol` has a **single load path** - it reads `data/lexicon/` Parquet
> only and raises `CorpusNotFoundError` when absent (4.2). `pyarrow` is a base
> dependency; `duckdb` (the `store` extra) backs the inspect/QA path alone. See
> [`04_store_layer.md`](04_store_layer.md), [`04.1_sqlite_mode.md`](04.1_sqlite_mode.md),
> [`04.2_seed_data.md`](04.2_seed_data.md).

### Storage format, git-LFS friendliness, and scaling

The shipped dataset should stay **git-LFS friendly**: large, mostly-append-only
data files tracked through LFS so the main repo history stays light, while small
schemas and loaders live in normal git. This needs a dedicated analysis (its own
sub-plan) covering:

- **Format choice** - line-oriented CSV/JSONL diffs and appends cleanly and is
  LFS-friendly; a single SQLite file is queryable and compact but is an opaque
  binary blob that LFS re-uploads wholesale on every change. Question: can a DB
  meaningfully live in LFS, or is it only worth it once read patterns demand
  indexed queries?
- **Scale estimate** - OMW across five languages is on the order of 10^5 synsets
  and 10^6 senses; estimate on-disk size per format and the cost of loading it
  all into memory at import time (the current model) versus lazy/indexed access.
- **Performance and limits** - import-time load latency, memory footprint, and
  the point at which the in-memory `_LEMMAS_BY_ID` approach stops scaling and a
  real index (SQLite FTS, or an on-disk key-value store) is warranted.

Provisional lean: keep ingestion outputs as partitioned JSONL/CSV under LFS;
revisit a SQLite build artifact only if query latency or memory become real
problems. The analysis sub-plan confirms or overturns this.

**Decision (phase 3, measured).** Experiments at the OMW 5-language scale (1M
senses; see [`03_storage_indexing.md`](03_storage_indexing.md) "Decision memo")
settle it on two separable axes:

- **Ship Parquet+zstd, partitioned per table and per language** (`senses`/
  `lemmas`) under git-LFS - ~8.6x smaller than JSONL (40.9 vs 350.3 MB total),
  every per-table file < 25 MB, and directly DuckDB-queryable for build/QA. As
  JSONL the `senses` table (227 MB) blows past GitHub's 100 MB hard limit, so the
  big tables need LFS regardless and JSONL's diff benefit is lost there.
- **Ship *all* tables as Parquet under LFS, including the small curated ones, for
  uniformity** (one distribution path, no special cases): a 50k-row textual diff
  is not meaningfully reviewable, and a model change rewrites every JSONL line, so
  line-diffability is a false comfort. Human inspection/editing is an explicit
  workflow over the Parquet (DuckDB SQL / a thin `inspect` CLI for reading;
  `export_table`->edit JSONL->`import_table` with pydantic validation for edits),
  not a committed line-oriented file; schema changes regenerate from ingestion.
- **Runtime: in-memory dicts only for the tiny sample data; promote the hot
  tables to SQLite indexed point lookups for the full corpus.** The full graph as
  pydantic dicts is ~1.9 GB resident (infeasible on a 512 MB dyno); SQLite gives
  ~30 us point lookups at ~0 resident. DuckDB is ~500x slower on point lookups
  (16 ms) - a build/QA tool, not the hot path. Do not ship a `.duckdb`/`.sqlite`
  as the canonical artifact; any runtime SQLite is built from the Parquet. Every
  filter/adjacency access needs an explicit index (a raw scan is ~150 ms).
  *(Superseded by 4.1/4.2: the runtime is **SQLite-only** for both sample and full
  corpus - no in-memory dict mode - and the store reads Parquet only, so SQLite is
  always built from `data/lexicon/`. DuckDB-as-build/QA-tool and the
  Parquet-as-source-of-truth points stand.)*

### Why the edge table over embedded `false_friends`

- **Lean payloads** - `GET /api/v1/lemmas/{id}` returns a clean token; heavy
  relationship graphs are fetched only when building a vocabulary-trap exercise.
- **Single-row ingestion** - a CSV/LLM loader appends one row to
  `false_friends.csv` instead of fetching, editing, and re-saving two lemma rows.
- **No symmetry bugs** - the canonical ordering means the link cannot be added on
  one side and forgotten on the other.
- **Reusable** - the same pattern fits any explicit token-to-token edge (e.g.
  irregular cognate pairs that do not share one clean concept).

## Semantic relations beyond false friends

False friends are one explicit edge type; WordNet/OMW carry several more that are
useful for a learner app. We keep the concept layer flat (sense grouping only) in
the first cut, but design the edge table to generalize so these can be added
without reshaping the model. Each is a typed edge; the concept-to-concept ones
reuse the canonical-ordering trick from `FalseFriendRelation`.

- **Hypernymy / hyponymy (is-a)** - the WordNet backbone. A *hypernym* is a more
  general concept ("animal" is a hypernym of "dog"); a *hyponym* is more specific.
  Directional, so no canonical reordering: store as
  `(parent_concept_id, child_concept_id)`. Useful for category drills and for
  grading difficulty (more specific = usually rarer/harder).
- **Antonymy (opposites)** - "hot" vs "cold". In WordNet antonymy is a
  *lemma*-level relation (between lemma senses), not a synset-level one, so model
  it as a symmetric lemma-to-lemma (or sense-to-sense) edge, like false friends.
  Feeds opposite-matching exercises and distractor generation.
- **Meronymy (part-of)** and other relations exist in WordNet too but are lower
  priority; the generic edge model below should not preclude them.

A single generic table covers the concept-to-concept cases:

```python
class ConceptRelation(BaseModel):
    """A typed edge between two concepts (e.g. hypernymy)."""
    concept_id_a: str
    concept_id_b: str
    relation_type: str          # "hypernym" (a is hypernym of b), "meronym", ...
    # symmetric types (e.g. "related") get canonical ordering; directional ones do not
```

Antonymy, being lemma-level, stays on a lemma/sense edge table parallel to
`FalseFriendRelation` rather than `ConceptRelation`. OMW exposes all of these via
the `wn` library, so ingestion is mostly a matter of choosing which relation
types to import.

## What we want to do with the concept model

Grounding from `lang-tutor` exercises and the `03-exercise-framework` notes:

- **Synonym / dialect drills** - pick a `Concept` whose `lemmas[lang]` has more
  than one entry. Feeds a pair-matching variant ("trem" = "comboio") and lets the
  tutor teach BR vs PT register.
- **Lemma-to-definition pair matching** - the framework already lists a
  word-to-definition variant of `pair_matching`; concept `definitions` are the
  natural source of the gloss side.
- **Cognate flashcard decks** - gather a concept's cross-lingual lemmas and rank
  by string similarity to surface "free" vocabulary for the learner.
- **False-friend warnings / trap exercises** - on lemma selection, hit
  `_FALSE_FRIENDS_BY_LEMMA_ID`; if an edge exists, show the `explanation_notes` in
  the learner's language as a warning or quiz distractor.
- **Better translation lookups** - `pair_matching` currently relies on
  `Lemma.translations[target]` and raises `MissingTranslationError` when absent.
  Concepts can supply translations transitively (token -> concept ->
  lemmas[target]), filling gaps that the flat `translations` dict misses.
- **Disambiguation in the conversational tutor** - when the LLM flags a lemma the
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

The hard part is mapping lemmas onto OMW synsets and collapsing WordNet's
fine-grained senses into learner-appropriate granularity. That is where an LLM
earns its keep (and is verifiable against OMW), rather than hallucinating
definitions from scratch.

### Why not the alternatives as primary source

- **Wiktionary alone** - no cross-lingual concept ids (you would rebuild synset
  clustering yourself) and a viral license.
- **LLM alone** - no ground truth, token cost, and needs validation against
  something, which would be OMW anyway.

### Licensing - free and open dataset

The end product ships as a **free and open-source dataset**. That goal constrains
the source mix:

- **OMW concept core is Apache-2.0** - permissive, no share-alike, safe as the
  backbone of an openly-licensed dataset.
- **Wiktionary enrichment is CC-BY-SA (share-alike, viral)** - mixing it into the
  core would force the whole dataset under CC-BY-SA. Options: (a) keep the
  CC-BY-SA enrichment in a clearly separated, separately-licensed layer with
  attribution, (b) accept CC-BY-SA for the entire shipped dataset as an
  acceptable open license, or (c) drop Wiktionary text and only use it to guide
  LLM enrichment that produces freshly-written glosses. The license choice for
  the enrichment layer is an open question (see below); the core stays
  permissive regardless.
- **`wordfreq` is MIT**; per-list frequency sources (SUBTLEX/OpenSubtitles) must
  be license-checked individually before shipping.

Ship a dataset card recording each source, its license, and required attribution.

### First slice

1. `pip install wn`, download `omw` for en/pt/es/fr/it.
2. Export synsets to `data/bootstrap/concepts.csv` (concept id =
   `c__{slug}__{hash[:12]}` derived from the ILI key, `definitions`, `lemmas`).
3. Emit the matching `Lemma` rows and `Sense` edges straight from the synset
   members (fresh sample data, not a migration of the old 50 lemmas). Use the LLM
   only to collapse over-fine senses to learner granularity.
4. Enrich sparse glosses/examples from kaikki where needed, and attach token
   frequency from `wordfreq`.

Sources: [Open Multilingual Wordnet](https://omwn.org/),
[`wn` PyPI](https://pypi.org/project/wn/) /
[goodmami/wn](https://github.com/goodmami/wn),
[OMW Portuguese license](https://github.com/omwn/omw-data/blob/main/wns/por/LICENSE),
[wiktextract](https://github.com/tatuylonen/wiktextract) /
[kaikki.org](https://kaikki.org/dictionary/index.html).

## Uplift plan (no data migration)

There is no data-migration burden here, so we do not carry one. The current
state is small and disposable:

- Only **~50 basic bootstrap lemmas** exist, and they are explicitly sample data.
- The **sole consumer is `lang-tutor`, and it only consumes a lemma list** (text /
  language / part-of-speech) - none of the heavy `translations` / `false_friends`
  / `glosses` fields.

Migrating that sample data onto concepts costs more than it is worth. Decision:
**replace the model outright and regenerate fresh sample data** from the new
ingestion pipeline, rather than backfilling the old rows.

Uplift steps:

1. Define the new models (`Lemma` thin, `Concept`, `Sense` edge, the relation
   edge tables) - the old flat fields (`translations`, embedded `false_friends`,
   canonical `glosses`) are dropped, not deprecated.
2. **`lang-tutor` is ours and moves in lockstep**, so there is no external
   contract to freeze: it still only needs `text`, `language`, `part_of_speech`,
   but we can rename/reshape and update the consumer in the same change rather
   than preserving the old surface.
3. Generate new sample data (a handful of concepts + their lemmas + a few example
   false-friend / relation edges) directly from the ingestion pipeline, replacing
   the old bootstrap CSVs.
4. Point `lemma_store` at the new data files.

Id schemes:

- `lemma_id` stays sha1 of `language::normalized` (16 hex chars).
- **Concept ids: `c__{slug}__{hash[:12]}`** - readable slug plus a hash safety
  net (resolves the slug-vs-hash open question). A deduplication pass catches the
  colliding slugs that should not exist in theory.

The `02-shared-data-layer` open question on glosses ("per-sense vs flattened")
is answered by this model: a sense maps to a concept, and the concept owns the
canonical gloss.

## Resolved (folded into the sections above)

- **Class name: `Word` vs `Lemma`?** Resolved: `Lemma` (literature term),
  renamed in the preliminary phase 1. See "Naming: `Lemma`, not `Word`".
- **Concept ids: slug vs hash?** Resolved: `c__{slug}__{hash[:12]}` - readable
  slug plus hash safety net, with a dedup pass for colliding slugs. See "Uplift
  plan".
- **Bootstrap source.** Resolved: OMW via `wn` as the concept backbone,
  Wiktionary for enrichment, LLM for mapping only. See "Bootstrap source".
- **Migration of existing data.** Resolved: no migration - the 50 sample lemmas
  are disposable and `lang-tutor` only needs a lemma list; regenerate fresh
  sample data. See "Uplift plan".
- **Relations beyond false friends.** Resolved into a design: model hypernymy /
  hyponymy and antonymy as typed edges, kept flat for the first cut. See
  "Semantic relations beyond false friends".
- **Concept granularity.** Resolved as a direction: start with WordNet synsets
  as-is, then merge closely related senses or add a "concept cluster" layer above
  synsets if too fine. Confirmed during the ingestion phase.
- **Storage format / git-LFS.** Resolved (phase 3, refined 4.1/4.2): ship **all
  tables as Parquet+zstd under git-LFS** (large tables partitioned per language),
  no committed DB blob and no line-oriented files. The runtime is a **SQLite-only**
  engine built from that Parquet; the store reads Parquet only (single load path,
  `CorpusNotFoundError` when absent). DuckDB is build/QA only. See "Storage format,
  git-LFS friendliness, and scaling" and [`03_storage_indexing.md`](03_storage_indexing.md).
- **Promote the sense edge now, or later?** Resolved (phase 2): promote now. The
  explicit `Sense` is the canonical membership record and hosts per-sense frequency
  and CEFR; `Lemma.concept_ids` and `Concept.lemmas` both drop as derivable. See
  "Modeling implication: an explicit sense edge".
- **Persistence vs representation.** Resolved (phase 2): persisted models are thin,
  id-only, drift-free records (the on-disk source of truth); convenience navigation
  (`sense.lemma`, `sense.concept`, `lemma.senses`, computed `concept.lemmas`) is an
  in-memory representation concern, hydrated by the store as serialization-excluded
  fields in phase 4. See [`02_core_models.md`](02_core_models.md).
- **Glosses on `Lemma` vs `Concept`.** Resolved (phase 2): glosses move entirely to
  `Concept.definitions`; `Lemma` keeps none. Raw source glosses are not carried as
  provenance now; if wanted they return in the ingestion phase (5) where they are
  produced.
- **Store layer, indexes, and hydration.** Resolved (phase 4, refined 4.1/4.2):
  built `LexiconStore` with the full query surface over a Parquet codec seam. The
  engine is a **single indexed SQLite database** (4.1 removed the resident dicts,
  eager `_hydrate()`, and the `LexiconStoreMode`/`SqliteModeNotImplementedError`
  seam); back-refs (`lemma.senses`/`concepts`, `concept.senses`/`lemmas`,
  `sense.lemma`/`concept`) are `exclude=True` fields filled **on demand** by the
  `hydrate_*` methods and read through `resolve_*` guards; circular refs resolved
  via `model_rebuild()` in the store module. The `Lemma.concepts` back-ref is a
  hydrated field (the phase-2 drift argument applies only to the *persisted*
  shape). `from_data_fol` reads `data/lexicon/` Parquet only - one load path,
  `CorpusNotFoundError` when absent (4.2). Webapp gained concept/relation read
  endpoints; a `corpus.py` inspect/edit surface and a `notebooks/lexicon_corpus/`
  driver (with a `parquetize_seed.ipynb` for the sample) replace the dropped
  human-readable artifact. See [`04_store_layer.md`](04_store_layer.md),
  [`04.1_sqlite_mode.md`](04.1_sqlite_mode.md), [`04.2_seed_data.md`](04.2_seed_data.md).

## Open questions

- **Enrichment license.** How to handle CC-BY-SA Wiktionary text so the shipped
  dataset stays cleanly open: isolated separately-licensed layer, accept CC-BY-SA
  for the whole dataset, or use Wiktionary only to guide freshly-written LLM
  glosses. See "Licensing".
- **Sense-frequency source per language.** Token frequency is covered by
  `wordfreq`; sense-level frequency outside English has no clean source. Decide
  the approximation (split token frequency by WordNet sense-tag weights, or mark
  estimated). See "Lemma frequency".
- **CEFR complexity source per language.** Graded word lists exist for some
  languages (and with varied licenses); for the rest, decide the estimation blend
  (frequency band + morphology + LLM) and how heavily to lean on it. See "Lemma
  complexity".

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
- Internal: `lang_tools/lexicon/lemma.py`, `lemma_store.py`, `lemma_id.py`
  (renamed from `words/word.py`, `word_store.py`, `word_id.py` in phase 1);
  `linux-box-cloudflare/scratch_space/vibes/10-language-overview/`
  (`02-shared-data-layer.md`, `03-exercise-framework.md`).
