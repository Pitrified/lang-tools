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
store at load time and excluded from serialization, and is built in a later
phase. The persisted records never carry object back-references or derivable
membership.

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
