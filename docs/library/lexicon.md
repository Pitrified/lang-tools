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
the whole graph. It loads every table, builds the look-aside indexes the app
needs, and hydrates the representation-layer back-references the persisted models
leave empty. The module also exposes a process-wide default store (built at
import) and thin delegating helpers - the stable surface `lang-tutor` and the
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

After loading, the store populates the serialization-excluded back-references:
`sense.lemma` / `sense.concept`, `lemma.senses` / `lemma.concepts`, and
`concept.senses` / `concept.lemmas` (the last a per-language grouping). Read them
through the `resolve_*` accessors (`sense.resolve_lemma()`,
`lemma.resolve_senses()`, `concept.resolve_lemmas()`, ...): an object built ad
hoc - before the store hydrated it - raises `NotHydratedError`
(`SenseNotHydratedError` for a sense endpoint) rather than returning `None`
silently. The persisted `lemma_id` / `concept_id` stay the always-available
fallback.

The circular back-references (`Lemma` <-> `Sense` <-> `Concept`) are resolved by
calling `model_rebuild()` on all three classes in the store module, where every
referenced class is in the runtime namespace.

### Storage format and runtime modes

The corpus is **Parquet (zstd)** under `data/lexicon/`, one file per table, with
the large tables (`lemmas` / `senses`) partitioned per language, all under
git-LFS. The on-disk format is hidden behind a codec seam
(`lang_tools.lexicon.codec`, the optional `store` extra): the rest of the store
never imports `pyarrow`. The store serves the same query surface over two
engines - in-memory dicts (**resident mode**, the default for the small sample
data) and indexed SQLite point lookups (**SQLite mode**, for the ~1.9 GB-resident
full corpus; its indexed implementation lands with the ingestion phase). Until
the sample corpus is regenerated as Parquet, the default store keeps sourcing its
lemmas from the bootstrap CSVs.

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
