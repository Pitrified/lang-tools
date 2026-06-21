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

A `Concept` is a language-independent unit of meaning (a synset). It stores its
`id`, per-language canonical `definitions`, and the two concept-level enrichment
fields from phase 5.5 Step 4 - `lexfile` (the coarse WordNet lexicographer class,
e.g. `noun.motion`) and per-language `examples`. Both are ILI-keyed, so they are
the same in every language: OMW carries them on the English/Princeton synset and
they propagate to the concept (phase 5.54 Topics 1-2). Membership (which lemmas
belong to it) is not stored here - it is derivable from the `Sense` edges.

Granularity note: example sentences live at the granularity their source
provides. OMW examples are concept-level, so they go on `Concept.examples`;
`Lemma.examples` stays for genuinely lemma-level sources. Today only OMW fills
either, so `Lemma.examples` is empty in the build.

```python
from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.concept_id import concept_id

cid = concept_id("library-building", "omw-en-03660909-n")  # c__{slug}__{hash[:12]}
concept = Concept(
    id=cid,
    definitions={"en": "a place full of books"},
    lexfile="noun.artifact",
    examples={"en": ["she returned the books to the library"]},
)
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
  canonical-ordering trick. The initial build now populates the OMW `hypernym`
  edges (`concept_id_a` is the more specific child, `concept_id_b` its parent);
  **hyponymy is the same edge read in reverse**, so it is not stored separately,
  and a hypernym target that does not resolve to a concept is dropped and logged,
  never emitted half-formed. Antonymy is deferred (it is sense-level and needs its
  own future edge table, a sibling of `FalseFriendRelation`).

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
corpus on load. There is no resident/SQLite dual mode: the full corpus as
in-memory pydantic dicts is ~1.9 GB resident, so a single SQLite code path serves
both the tiny sample and the full corpus at ~0 resident. `from_data_fol` has a
**single load path**: it reads the Parquet under `data/lexicon/` and raises
`CorpusNotFoundError` when the folder holds no corpus.

The load is lean and cached (phase 5.3). By default `from_data_fol` **streams**
each table's lean Parquet rows straight into SQLite, one table at a time, without
building pydantic models - the profiling showed that retaining ~580k models is
what drove the load's memory peak (and made a small box swap-thrash / OOM). The
built database is **persisted** beside the corpus (`<corpus>/_store.sqlite`,
gitignored) and reused while a content signature over the Parquet files is
unchanged, so a warm load is a bare `sqlite3.connect` (~1 ms). A changed corpus
rebuilds automatically. Pass `validate=True` for the slower row-validating path
(every row parsed through its model, raising `MalformedRecordError` on a bad row),
or `db_path=":memory:"` / `use_cache=False` to skip the persisted cache. For
bulk/overview reads of the full corpus prefer `inspect_table` (DuckDB) over
`get_all_*`, which reconstructs every model.

The full corpus is produced by the ingestion phase under `data/lexicon/`. For
local development the committed JSONL **sample seed** under `data/bootstrap/` (a
small, diffable, text-only fixture) is parquetized into its **own** corpus at
`data/bootstrap/lexicon/` by the `parquetize_seed.ipynb` notebook - kept separate
from the real `data/lexicon/` build so the two never overwrite each other. The
seed is an input, never a runtime source - the store always reads Parquet.

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
  Both the download (`download_omw`) and the read select by a **single explicit
  lexicon** via the `OMW_LEXICONS` map / `_omw_lexicon` helper, never the `omw`
  collection or a bare `lang=` filter: the collection pulls every member wordnet
  and a bare `lang` can match two installed wordnets (`it` matches both `omw-it`
  and `omw-iwn`) and silently merge them, breaking determinism. An unmapped
  language raises `UnknownOmwLanguageError`.
- **`sources.kaikki`** is enrichment only: `load_kaikki_entries` keeps the
  glosses and example sentences (unlike `load_wiktionary_jsonl`) so `transform`
  can fill sparse `Concept.definitions` and attach `Lemma.examples`. It never
  adds rows, and it stays a **lazy line-by-line stream** end to end
  (`load_sources` chains the per-language dumps; `transform` filters them against
  the bounded OMW lemma-key set), so the multi-hundred-MB dumps are never held
  resident.
- **`transform`** returns `TaggedTables` - the five tables plus a parallel
  per-row provenance tag (`omw` / `kaikki` / `llm` / `manual`). OMW rows are
  tagged `omw`; any row that gains CC-BY-SA kaikki content is re-tagged `kaikki`
  (the conservative, license-isolating choice). The kaikki iterator is consumed
  exactly once and only matching entries are retained, so peak enrichment memory
  is bounded by the OMW backbone, not the dump size.
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

### Stage 0 dataset staging (phase 5.54)

Separate from the build, `ingestion.staging` pulls the enrichment-candidate
datasets into a read-only cache under `data/_raw/lexicon/staging/` so the
phase-5.54 exploration notebooks read clean inputs. Staging never writes the
source-of-truth Parquet; it only fills the gitignored cache and a `_staging.json`
manifest that records each dataset's source, version, and **license** (so the
phase-10 posture is auditable from the cache alone). Each adapter follows the
`sources` discipline: network and optional-dependency work is isolated in the
impure functions, while the parsers, query builders, and the lemma index are pure
and unit-tested.

- **`staging.tatoeba`** - `download_tatoeba_sentences` fetches the per-language
  sentence export (HTTPS, isolated); `parse_tatoeba_tsv` and
  `build_lemma_sentence_index` are pure. The index is a **sense-blind** lemma-only
  join (word-boundary, accent-insensitive, capped per lemma), so it is for
  examples only - never glosses.
- **`staging.frequency`** - `stage_frequency_list` writes per-language
  `(word, rank, zipf)` via `wordfreq` (the lazy `enrich` extra; absence raises
  `EnrichDependencyMissingError`). This is the language-level frequency signal,
  distinct from concept commonness.
- **`staging.wikidata`** - the public SPARQL endpoint is throttled (a global count
  returns HTTP 429), so the viable source is the **CC0 lexeme dump**:
  `download_lexeme_dump` streams the ~590 MB `latest-lexemes.json.gz` (creating its
  dir, skipping if present), then `stream_lexeme_dump` / `parse_lexeme_dump_records`
  / `stage_wikidata_lexeme_dump` write per-language tables with exact counts.
  `probe_wikidata_lexemes` stays as a gentle SPARQL fallback (backs off on 429,
  count off by default).
- **`staging.cefr`** - graded lists for **validation only** (never merged, so even
  share-alike / non-commercial is fine). `download_cefr_source` fetches and parses a
  registered source by name; the Kelly en/it `.xls` lists are read via `xlrd` (their
  per-language sheets differ - en is `Word`/`CEFR`, it is `Lemma`/`Points`).
  `KNOWN_CEFR_SOURCES` records each candidate (Kelly en/it CC-BY-NC-SA, Oxford
  guidance-only, the pt/es/fr gap); `download_cefr_list` handles any delimited
  (CSV/TSV) URL and `stage_cefr_list` a local file.

`omw_cili_staged_records` records the OMW backbone and CILI resource (already
staged by `acquire.download_omw`) in the same manifest. The thin
`notebooks/lexicon_enrich/00_stage.ipynb` wires the calls and writes the manifest.

Five topic notebooks (`notebooks/lexicon_enrich/01_examples` ..
`05_complexity`) read that staged cache plus the OMW wordnets and end each in a
findings cell. They are exploration only (they use the `enrich` extra's `pandas`
/ `matplotlib`, never imported by the package) and back the phase-5.54 decisions:
OMW examples / definitions / lexfile / relations are carried on the English
synset but every synset is 100% ILI-linked, so they propagate to the concept for
free; SemCor concept commonness correlates with per-language frequency (en 0.47,
predicts es 0.34 / it 0.49); and lemma frequency is the strongest difficulty
signal against Kelly CEFR (-0.66), with the concept-level call holding in 87% of
en->it cases. See [`05.54_data_enrich.md`](../../scratch_space/09_concept_model/05.54_data_enrich/05.54_data_enrich.md).
