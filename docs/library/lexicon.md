# Lexicon

The `lang_tools.lexicon` package owns the canonical concept-centric lexical
model and its ingestion pipelines. Meaning is modelled as a small graph: thin
lemmas (tokens) link to language-independent concepts (synsets) through explicit
sense edges, and relations between entities live in their own decoupled edge
tables.

## Persistence vs representation

The models below are the **persisted** shape: thin, id-only records that are the
on-disk source of truth. Each edge is stored once, in one place, so nothing
drifts. Convenience navigation between objects (`sense.lemma`, `concept.lemmas`,
`lemma.senses`, ...) is a **representation-layer** concern: it is hydrated by the
store at load time (see "Store and queries") and excluded from serialization.
The persisted records never carry object back-references or derivable
membership, so `model_dump()` stays byte-stable.

## `Lemma` model

A `Lemma` is the lexical *token*: one surface form in one language. It always
carries a stable `id`, a normalised form, an optional part of speech, topic
tags, curated examples, and provenance. The id is derived from
`(text, language)` after normalisation, so two records that differ only in case
or accents collide cleanly. The lemma stores **no meaning of its own** -
definitions, cross-lingual links, frequency, and CEFR complexity live on the
`Concept` and `Sense` it participates in.

```python
from lang_tools.lexicon.lemma import Lemma

lemma = Lemma(text="Café", language="fr", part_of_speech="noun", topics=["food"])
lemma.id            # 16-char sha1 prefix
lemma.normalized    # 'cafe'
lemma.has_accent    # True
lemma.length        # 4
```

## `Concept` model

A `Concept` is a language-independent unit of meaning (a synset). It stores only
its `id` and per-language canonical `definitions`; membership (which lemmas
belong to it) is not stored here - it is derivable from the `Sense` edges.

```python
from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.concept_id import concept_id

cid = concept_id("library-building", "omw-en-03660909-n")  # c__{slug}__{hash[:12]}
concept = Concept(id=cid, definitions={"en": "a place full of books"})
```

The id is supplied (not computed): it is built at ingestion from the stable
OMW/ILI source key via `concept_id`, and the model validates its
`c__{slug}__{hash}` shape.

## `Sense` model

A `Sense` is the explicit `lemma_id <-> concept_id` edge and the canonical
membership record. It also hosts the per-sense signals that must not live on the
token - `token_frequency`, `sense_frequency`, and `cefr_level` (with their
`*_is_estimated` flags). The "bank" polysemy trap is the rationale: one lemma's
two meanings differ in frequency and difficulty, so those values belong on the
sense. The id is computed from the endpoint pair.

```python
from lang_tools.lexicon.sense import Sense

sense = Sense(lemma_id=lemma.id, concept_id=concept.id, cefr_level="B1")
sense.id            # 16-char sha1 prefix over (lemma_id, concept_id)
```

The per-sense values are defined now and populated later in the pipeline.

## Relation edge tables

Relations are stored as standalone edges, never embedded on the entities they
connect:

- `FalseFriendRelation` is a symmetric lemma-to-lemma edge (a misleading
  cognate pair). Endpoints are held in canonical order
  (`lemma_id_a < lemma_id_b`) so each pair is stored once and dedups naturally.
- `ConceptRelation` is a typed concept-to-concept edge (`"hypernym"`,
  `"meronym"`, `"related"`, ...). Directional types keep their source/target
  order; symmetric types (see `SYMMETRIC_CONCEPT_RELATIONS`) reuse the
  canonical-ordering trick.

Both reject self-edges with a `SelfRelationError`.

## Store and queries

`LexiconStore` (`lang_tools.lexicon.lemma_store`) is the read/query layer over
the whole graph. It builds a single **indexed SQLite database** from the corpus
and answers every query with `SELECT`s, reconstructing the thin models through
the codec. The module also exposes a process-wide default store (built lazily on
first use) and thin delegating helpers - the stable surface `lang-tutor` and the
webapp consume:

- Lemmas: `get_all_lemmas`, `get_lemma_by_id`, `get_lemmas_by_language`,
  `get_lemmas_by_topic`, `get_lemmas_filtered`.
- Concepts: `get_all_concepts`, `get_concept_by_id`.
- Adjacency: `concepts_for_lemma`, `lemmas_for_concept` (optional `language`),
  `senses_for_lemma`, `senses_for_concept`.
- Edges: `get_false_friends_for_lemma` (returns `(other_lemma, edge)` pairs,
  resolving symmetry), `concept_relations_for` (optional `relation_type`).

These are point lookups and bounded adjacency joins, not aggregations.

### Hydration and the guard

The serialization-excluded back-references (`sense.lemma` / `sense.concept`,
`lemma.senses` / `lemma.concepts`, `concept.senses` / `concept.lemmas`) are
filled **on demand**, per call, by the store's `hydrate_lemma`,
`hydrate_concept`, and `hydrate_sense` methods - a bounded 1-2 hop SQLite read,
not an eager whole-graph pass. Hydrated instances are built fresh on each call,
so there is no shared-instance identity. Read the back-references through the
`resolve_*` accessors (`sense.resolve_lemma()`, `lemma.resolve_senses()`,
`concept.resolve_lemmas()`, ...): an object that was not hydrated raises
`NotHydratedError` (`SenseNotHydratedError` for a sense endpoint) rather than
returning `None` silently. The persisted `lemma_id` / `concept_id` stay the
always-available fallback.

The circular back-references (`Lemma` <-> `Sense` <-> `Concept`) are resolved by
calling `model_rebuild()` on all three classes in the store module, where every
referenced class is in the runtime namespace.

### Storage format and the runtime engine

The source-of-truth corpus is **Parquet (zstd)** under `data/lexicon/`, one file
per table, with the large tables (`lemmas` / `senses`) partitioned per language,
all under git-LFS. The on-disk format is hidden behind a codec seam
(`lang_tools.lexicon.codec`). `pyarrow` is a base dependency (reading the corpus
is the store's only load path); `duckdb`, the `store` extra, backs the inspect/QA
path alone.

The runtime engine is **SQLite only** - one indexed database, built from the
corpus on load and never committed (rebuilt from its source each time). There is
no resident/SQLite dual mode: the full corpus as in-memory pydantic dicts is
~1.9 GB resident, so a single SQLite code path serves both the tiny sample and
the full corpus at ~0 resident. `from_data_fol` has a **single load path**: it
reads the Parquet under `data/lexicon/` and raises `CorpusNotFoundError` when the
folder holds no corpus. The full corpus is produced by the ingestion phase; for
local development the committed JSONL **sample seed** under `data/bootstrap/` (a
small, diffable, text-only fixture) is turned into that Parquet by the
`parquetize_seed.ipynb` notebook. The seed is an input, never a runtime source -
the store always reads Parquet.

### Inspect and edit

Nothing human-readable is committed, so `lang_tools.lexicon.corpus` exposes
explicit operations over the Parquet (driven from `notebooks/lexicon_corpus/`, a
thin caller):

- `inspect_table(name, *, data_fol, lang=, where=, limit=)` runs read-only
  DuckDB SQL over the Parquet - no import step.
- `export_table` / `import_table` are the validated edit round-trip: export to a
  transient JSONL, hand/LLM-edit it, then re-import. The import validates **every
  row through the pydantic model** (a renamed/missing column or bad value raises
  `MalformedRecordError`) before rewriting the canonical Parquet. The JSONL is
  scratch, never committed; schema changes regenerate from ingestion, not
  line-patched.

## Ingestion

`lang_tools.lexicon.ingestion` exposes three loaders, all yielding thin `Lemma`
instances tagged with the originating source:

- `load_wiktionary_jsonl(path, language=...)` reads kaikki.org-style JSONL
  Wiktionary dumps. Filters by part-of-speech and skips inflected-form
  pointers by default. Senses are still parsed but their glosses become
  `Concept.definitions` during the concept-mapping phase, not lemma fields.
- `load_csv(path)` reads a flat CSV with required columns `text` and
  `language` plus optional `part_of_speech`, `topics` / `secondary_topics`, and
  `example_sentence` / `example_translation`. Other columns (e.g. legacy
  frequency or translation columns) are ignored. Raises
  [`CSVColumnsMissingError`](../reference/lang_tools/lexicon/ingestion/csv_loader/)
  on missing required columns.
- `load_static_list(entries)` ingests an in-memory list of dicts (the
  `worldly-words` flow).

`merge_lemmas(left, right)` and `deduplicate(lemmas)` collapse records that
share an id, merging their topics, examples, and sources.

### Initial build pipeline (phase 5)

On top of the per-file loaders, `ingestion` ships the one-time **initial build**
that populates the whole corpus from external sources. It is linear by design -
the Parquet tables are the source of truth, so there is no base/overlay split:

```
sources (OMW via wn, kaikki JSONL)
  -> acquire   (download -> data/_raw/lexicon/ cache + _build.json manifest)
  -> transform (raw -> source-tagged concepts/lemmas/senses)
  -> write     (codec _dump_table -> data/lexicon/*.parquet, the source of truth)
  -> sample    (carve a small slice for lang-tutor + tests)
```

- **`acquire`** pulls the raw sources into the gitignored, regenerable cache and
  pins their exact versions in a `_build.json` manifest. `download_omw` wraps
  `wn` (the `ingest` extra); `fetch_kaikki` is a plain HTTPS GET; the manifest is
  the only seam a future re-ingestion merge diffs against (the machine baseline
  is *reconstructible* from the pinned cache, so no base snapshot is committed).
- **`sources.omw`** is the concept backbone: `wn_synset_entries` flattens OMW
  synsets (the only place that touches `wn`), and the pure `group_to_records`
  groups them by shared ILI key into one `Concept` per meaning (this is the
  cross-lingual cognate grouping) plus the member `Lemma`s and `Sense` edges.
- **`sources.kaikki`** is enrichment only: `load_kaikki_entries` keeps the
  glosses and example sentences (unlike `load_wiktionary_jsonl`) so `transform`
  can fill sparse `Concept.definitions` and attach `Lemma.examples`. It never
  adds rows.
- **`transform`** returns `TaggedTables` - the five tables plus a parallel
  per-row provenance tag (`omw` / `kaikki` / `llm` / `manual`). OMW rows are
  tagged `omw`; any row that gains CC-BY-SA kaikki content is re-tagged `kaikki`
  (the conservative, license-isolating choice).
- **`build_initial`** wires it together: transform, write each table through the
  codec with its tags, write the manifest, then carve and (optionally) write a
  sample slice. Thin notebooks under `notebooks/lexicon_ingest/` drive it.

The optional LLM granularity-collapse pass (over-fine WordNet senses ->
learner granularity) is a deferred seam: the deterministic OMW-as-is output is
the default and the only thing the build produces today.

#### Provenance column

The provenance tag lives **on disk only**: the codec writes it as an extra
`source` Parquet column when `_dump_table` is given parallel `sources=`, and
always drops it on load so it never reaches the thin pydantic models (the same
trick as the computed `id`). It is the one lightweight seam the deferred
re-ingestion merge needs - refresh machine rows, preserve hand-curated `manual`
ones - and it keeps the runtime store (which loads through the codec) untouched.
