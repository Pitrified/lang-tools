---
status: draft
---

# Phase 2 - core data models

> Draft. Scope sketch to hold the overarching story; not yet the plan of record.

## Overview

Introduce the concept-centric model on top of the thin `Lemma` left by phase 1.
This is the structural heart of the effort: it defines the Pydantic models every
later phase reads and writes. Context:
[`00-concepts-brainstorm.md`](00-concepts-brainstorm.md), "Proposed models" and
"Lemma frequency". Depends on phase 1 (naming) and informs phase 3-4 (storage).

## What this phase will cover

- **`Lemma` (thin)** - keep `text`, `language`, `normalized`, `part_of_speech`;
  add `concept_ids: list[str]`. Drop the heavy fields (`translations`, embedded
  `false_friends`, canonical `glosses`) - no migration, since data is regenerated
  (phase 9).
- **`Concept`** - `id` (`c__{slug}__{hash[:12]}`), `definitions: dict[str, str]`,
  `lemmas: dict[str, list[str]]`. The language-independent synset.
- **`Sense` edge** - the explicit `lemma_id <-> concept_id` object. The phase will
  settle the open question of promoting it now vs keeping the flat `concept_ids`
  list; the lean is to promote it, because frequency (phase 6) and CEFR
  complexity (phase 6) are both per-sense and need a home. Carries the
  `token_frequency` / `sense_frequency` / `cefr_level` fields (populated later).
- **`FalseFriendRelation`** - decoupled, canonically-ordered (`lemma_id_a <
  lemma_id_b`) edge with `similarity_score` and per-language `explanation_notes`.
- **Generic `ConceptRelation`** - typed concept-to-concept edge stub (hypernymy
  etc.), defined here but populated in phase 7.
- **Id helpers** - `lemma_id` (exists), new `concept_id` (slug+hash) and
  `sense_id` deterministic constructors, plus the dedup discipline for colliding
  slugs.

## Open points to resolve here

- Promote `Sense` now or defer (leaning: promote).
- Do glosses also stay on `Lemma` as provenance, or only on `Concept`?
- Exact slug derivation for `concept_id` (from ILI key vs English gloss).

## Out of scope

- Loading/indexing these models from disk (phase 4) and the storage-format choice
  (phase 3); ingestion that fills them (phase 5); relation/frequency population
  (phases 6-7).

## Done when (draft)

- Models defined with docstrings and validators; unit tests cover id determinism,
  canonical ordering, and round-trip serialization.
- `uv run pytest && uv run ruff check . && uv run pyright` passes.
