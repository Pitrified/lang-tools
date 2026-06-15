---
status: draft
---

# Phase 7 - semantic relations

> Draft. Scope sketch to hold the overarching story; not yet the plan of record.

## Overview

Populate the typed edges beyond false friends - hypernymy/hyponymy and antonymy -
using the generic edge tables stubbed in phase 2 and the relation data OMW
already carries. Kept deliberately small for the first cut; the concept layer
stays flat (sense grouping) and these edges sit beside it. Context:
[`00-concepts-brainstorm.md`](00-concepts-brainstorm.md), "Semantic relations
beyond false friends". May fold into phase 5 (ingestion) since OMW supplies the
edges in the same traversal.

## What this phase will cover

- **Hypernymy / hyponymy (is-a)** - the WordNet backbone. Directional, stored on
  `ConceptRelation` as `(parent_concept_id, child_concept_id)` with
  `relation_type="hypernym"`; no canonical reordering. Powers category drills and
  difficulty grading (more specific tends to be rarer/harder).
- **Antonymy (opposites)** - a *lemma*-level relation in WordNet, so stored on a
  symmetric lemma/sense edge table parallel to `FalseFriendRelation`, not on
  `ConceptRelation`. Powers opposite-matching exercises and distractors.
- **Meronymy (part-of)** and other WordNet relations - lower priority; confirm the
  generic `ConceptRelation` model does not preclude adding them later.
- **Ingestion hook** - extend the phase-5 OMW pass (via `wn`) to emit the chosen
  relation types; choose which types to import and at what depth.

## Open points to resolve here

- Which relation types ship in the first cut (hypernymy + antonymy proposed).
- Traversal depth / pruning so the edge tables stay LFS-friendly (tie back to
  phase 3).

## Out of scope

- A hierarchical "concept cluster" layer above synsets (only if granularity from
  phase 5 proves too fine); exposing relations in exercises (`lang-tutor`).

## Done when (draft)

- Hypernymy and antonymy edges loaded and queryable via the phase-4 store over the
  five languages; adjacency lookups covered by tests.
- `uv run pytest && uv run ruff check . && uv run pyright` passes.
