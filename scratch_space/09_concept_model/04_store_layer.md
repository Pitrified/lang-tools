---
status: draft
---

# Phase 4 - store layer + indexes

> Draft. Scope sketch to hold the overarching story; not yet the plan of record.

## Overview

Grow `lemma_store` (renamed in phase 1) from a flat lemma registry into the
read/query layer for the whole lexical graph: lemmas, concepts, senses, and edge
tables, with the look-aside indexes the app needs. Implements the format decided
in phase 3 over the models from phase 2. Context:
[`00-concepts-brainstorm.md`](00-concepts-brainstorm.md), "Storage and indexing".

## What this phase will cover

- **Registries** - load concepts and false-friend/relation edges alongside lemmas
  at import time (or lazily, per phase 3): `_ALL_LEMMAS`/`_LEMMAS_BY_ID`,
  `_CONCEPTS_BY_ID`, `_ALL_FALSE_FRIENDS`, `_ALL_CONCEPT_RELATIONS`, and the
  sense table.
- **Look-aside indexes** - `_FALSE_FRIENDS_BY_LEMMA_ID` (symmetric), concept/
  sense indexes, and the relation adjacency needed for traversal.
- **Query helpers** - `get_false_friends_for_lemma(lemma_id)`,
  `concepts_for_lemma(lemma_id)`, `lemmas_for_concept(concept_id, language=None)`,
  plus the existing lemma getters extended to the new shape. These are the stable
  surface `lang-tutor` and the webapp consume.
- **Webapp endpoints** - extend the `/api/v1/lemmas` router and add
  concept/relation read endpoints so the heavy graph is fetched only when needed
  (lean lemma payloads stay lean).
- **Loader robustness** - clear, named errors on malformed rows; dedup of
  colliding concept slugs flagged here.
- **Hydration of representation back-refs** - phase 2 defines the convenience
  navigation as store-hydrated, serialization-excluded fields (`sense.lemma`,
  `sense.concept`, `lemma.senses`, `concept.senses`, computed `concept.lemmas`).
  This phase populates them once at load time and owns their consistency. Carry the
  note from phase 2: an *unhydrated* `Sense` (one built ad hoc, e.g. by ingestion
  before the registries exist, or in a unit test) has `sense.lemma is None`. Decide
  the guard here - either a clear `SenseNotHydratedError` raised by the accessor, or
  lazy resolution through the store - rather than returning `None` silently and
  surprising callers. The persisted `lemma_id`/`concept_id` always remain the
  fallback path.

## Out of scope

- Producing the data files (phase 5); frequency/complexity values (phase 6) and
  relation contents (phase 7) - this phase wires the plumbing, not the payload.
- Any DB migration beyond what phase 3 selected.

## Done when (draft)

- Helpers return correct, indexed results over a small fixture dataset; symmetry
  and missing-id edge cases covered by tests.
- `uv run pytest && uv run ruff check . && uv run pyright` passes; `lang-tutor`
  still reads its lemma list unchanged.
