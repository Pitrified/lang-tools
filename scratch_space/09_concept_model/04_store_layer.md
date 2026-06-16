---
status: planned
---

# Phase 4 - store layer + indexes

## Overview

Grow `lemma_store` (renamed in phase 1) from a flat lemma registry into the
read/query layer for the whole lexical graph: lemmas, concepts, senses, and the
decoupled edge tables, with the look-aside indexes the app needs and the
representation-layer hydration that phase 2 deferred here. It implements the
storage format and access engine decided in phase 3 over the models from phase 2.
Context: [`00-concepts-brainstorm.md`](00-concepts-brainstorm.md), "Storage and
indexing"; [`02_core_models.md`](02_core_models.md), "Persistence vs
representation"; [`03_storage_indexing.md`](03_storage_indexing.md).

This phase is **plumbing, not payload**: it wires loaders, registries, indexes,
hydration, and query helpers, plus the HTTP read endpoints. It does **not**
produce the data (phase 5) or fill frequency/CEFR/relation values (phases 6-7);
it is exercised against a small fixture dataset.

Sequencing note (see "Sequencing with phase 3"): the **query surface defined
below is the design input phase 3 measures against**, so it is written first even
though the implementation waits on phase 3's format decision. Planning the two
phases together is deliberate - it sharpens phase 3's experiments and stops the
experiment code from being throwaway that this phase re-implements.

## Goals

1. Define the stable **read/query surface** for the whole graph (the contract
   `lang-tutor`, the webapp, and exercises consume) and the **access patterns**
   behind it - this doubles as phase 3's benchmark target.
2. Load and index every table (lemmas, concepts, senses, false-friend and
   concept-relation edges) behind a thin **codec seam** so the format chosen in
   phase 3 is swappable and the phase-3 experiment code promotes into the real
   loader instead of being rewritten.
3. Implement the **representation-layer hydration** phase 2 specified: populate
   the serialization-excluded back-references once at load time, with a single
   owner (the store) and a defined guard for unhydrated objects.
4. Extend the webapp with concept/relation read endpoints while keeping the lemma
   payload lean.
5. Keep `lang-tools` green over a fixture dataset with tests covering indexing,
   symmetry, hydration, and missing-id edge cases.

## Query surface & access patterns (the phase-3 benchmark target)

This is the contract and the exact set of reads phase 3 must measure. Each entry
notes the access pattern so the format/engine trade-off is grounded.

| Helper | Access pattern | Hot? |
| ------ | -------------- | ---- |
| `get_lemma_by_id(lemma_id)` | point lookup by primary key | **hot** |
| `get_lemmas_by_language(language)` | small filtered scan | warm |
| `get_lemmas_by_topic(topic)` / `get_lemmas_filtered(...)` | filtered scan | warm |
| `get_concept_by_id(concept_id)` | point lookup by primary key | **hot** |
| `concepts_for_lemma(lemma_id)` | adjacency over the sense table | **hot** |
| `lemmas_for_concept(concept_id, language=None)` | adjacency over the sense table, optionally bucketed by language | **hot** |
| `senses_for_lemma(lemma_id)` / `senses_for_concept(concept_id)` | adjacency over the sense table | warm |
| `get_false_friends_for_lemma(lemma_id)` | symmetric adjacency over the false-friend edges | warm |
| `concept_relations_for(concept_id, relation_type=None)` | typed/directional adjacency (phase 7 payload) | cold |

Characterisation for phase 3: the surface is **point lookups and bounded
adjacency joins**, not large aggregations. That favors in-memory dicts or SQLite
point lookups over a columnar analytical engine, and tells phase 3 exactly which
latencies to time (id lookups, sense-table adjacency, symmetric false-friend
fan-out) rather than guessing.

## Plan

All paths under `src/lang_tools/lexicon/` unless noted. The current
`lemma_store.py` already provides `_ALL_LEMMAS` / `_LEMMAS_BY_ID` and the lemma
getters; this phase generalises that pattern to every table.

### Codec seam (loader boundary)

- A thin `_load_table(name) -> list[<Model>]` / `_dump_table(...)` boundary that
  hides the on-disk format (JSONL / Parquet / SQLite, per phase 3) behind a
  stable signature. The phase-3 experiment serializers are written against this
  same seam so the winning codec is promoted here and the losers plus the timing
  harness are discarded.
- Format selection follows phase 3's decision; the rest of the store imports only
  the seam, never the format details.

### Registries

- Load each table at import (or lazily, per phase 3's memory finding):
  `_ALL_LEMMAS` / `_LEMMAS_BY_ID`, `_ALL_CONCEPTS` / `_CONCEPTS_BY_ID`,
  `_ALL_SENSES`, `_ALL_FALSE_FRIENDS`, `_ALL_CONCEPT_RELATIONS`.
- Primary-key dicts give the hot point lookups; the rest are derived indexes.

### Look-aside indexes

- `_SENSES_BY_LEMMA_ID` and `_SENSES_BY_CONCEPT_ID` (the adjacency that powers
  `concepts_for_lemma` / `lemmas_for_concept` / `senses_for_*`).
- `_FALSE_FRIENDS_BY_LEMMA_ID`: built by inserting each edge under **both**
  endpoints, since the persisted edge is canonically ordered (`lemma_id_a <
  lemma_id_b`) and stored once (see phase 2).
- `_CONCEPT_RELATIONS_BY_CONCEPT_ID`: adjacency for traversal; respects
  directional vs symmetric types from `relations.py`.

### Representation-layer hydration

- Add the serialization-excluded back-reference fields phase 2 specified
  (`Field(default=None, exclude=True, repr=False)`): `Sense.lemma`,
  `Sense.concept`, `Lemma.senses`, `Concept.senses`, and the computed
  `Concept.lemmas` grouping (per-language, derived from senses).
- The store is the **single owner**: it sets these once after all registries are
  loaded, in a `_hydrate()` pass. `exclude=True` keeps them out of `model_dump()`
  so the persisted shape from phase 2 is unaffected (the phase-2 round-trip tests
  still hold).
- **Unhydrated-object guard** (carried from phase 2): a `Sense` built ad hoc
  (ingestion before registries exist, or a unit test) has `sense.lemma is None`.
  Decision for this phase: the accessor raises a clear **`SenseNotHydratedError`**
  rather than returning `None` silently; the persisted `lemma_id` / `concept_id`
  remain the always-available fallback path. (Lazy resolution through the store
  was considered but rejected: it couples the model module to the store and hides
  the "you forgot to load" bug instead of surfacing it.)

### Query helpers

- Implement the full surface in the table above. `get_false_friends_for_lemma`
  returns each match as `(other_lemma, edge)` (resolving the non-self endpoint),
  mirroring the brainstorm sketch.
- These are the stable surface `lang-tutor` and the webapp consume; keep
  signatures additive so consumers migrate in phase 9.

### Webapp endpoints

- Extend `webapp/routers/lemmas_router.py` (lemma payload stays lean) and add
  concept/relation read endpoints so the heavy graph is fetched only when needed
  (e.g. building a vocabulary-trap exercise), not bundled into every lemma
  response.

### Loader robustness

- Clear, named errors on malformed rows (a `MalformedRecordError`-style
  exception rather than bare `ValueError`).
- Colliding concept slugs: detected and flagged at load (the `hash[:12]` suffix
  already keeps ids unique; readability disambiguation is an ingestion concern in
  phase 5, but the store warns on collisions so they are visible).

### Tests (`tests/lexicon/`, `tests/webapp/`)

- Index correctness over a small fixture: sense adjacency both directions,
  false-friend symmetry (one stored edge appears under both endpoints), concept
  relation directional vs symmetric traversal.
- Hydration: after load, `sense.lemma` / `concept.lemmas` resolve; `model_dump()`
  still carries no back-refs; an unhydrated `Sense` accessor raises
  `SenseNotHydratedError`.
- Missing-id edge cases return empty / `None` as specified, never raise.

## Sequencing with phase 3

Planned in lockstep with phase 3, executed staged:

1. **Now (planning):** this query surface + access-pattern list is fixed; it is
   phase 3's benchmark target.
2. **Phase 3 execution:** experiments measure *these* patterns (id lookups, sense
   adjacency, false-friend fan-out) per candidate format, writing the
   (de)serialization against the **codec seam** above - throwaway harness, but a
   reusable codec.
3. **Phase 3 decision:** format + access engine chosen with numbers.
4. **Phase 4 execution:** implement the store against the decision, promoting the
   winning codec.

The store implementation deliberately does **not** start before phase 3 decides,
so it is never built on an unvalidated format. See the mirrored note in
[`03_storage_indexing.md`](03_storage_indexing.md).

## lang-tutor status

Phase 2 already dropped fields `lang-tutor` reads (`translations`, `frequency`,
`glosses`), so `lang-tutor` stays red until its consumer uplift in **phase 9**.
This phase keeps the lemma read surface stable and additive so that uplift is
mechanical, but does not itself un-break `lang-tutor` (no concept/sense data
exists for it to consume until phase 5/9).

## Out of scope

- Producing the data files (phase 5); frequency/CEFR values (phase 6) and
  relation contents (phase 7) - plumbing only.
- The storage-format decision itself (phase 3); this phase consumes it.
- The `lang-tutor` consumer uplift and sample-data regeneration (phase 9).

## Done when

- The full query surface is implemented and indexed; hydration populates the
  excluded back-refs with the `SenseNotHydratedError` guard in place.
- Concept/relation read endpoints exist; the lemma payload stays lean.
- Tests cover indexing, symmetry, hydration, and missing-id edge cases over a
  fixture dataset.
- `uv run pytest && uv run ruff check . && uv run pyright` passes in `lang-tools`.
- Docs updated (`docs/library/lexicon.md` gains a store/query section); the
  tracking Log records the phase.
