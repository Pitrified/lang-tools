---
status: draft
---

# Phase 5 - initial ingestion pipeline

> Draft. Scope sketch to hold the overarching story; not yet the plan of record.

## Overview

Build the pipeline that produces the real lexical dataset from external sources,
in a deliberate order: OMW as the concept backbone, Wiktionary as enrichment, an
LLM for mapping/granularity only. Writes the formats from phase 3 into the
registries from phase 4. Context:
[`00-concepts-brainstorm.md`](00-concepts-brainstorm.md), "Bootstrap source".
This phase extends the existing `lexicon/ingestion/` subpackage.

## What this phase will cover (in order)

1. **OMW backbone** - via the `wn` library (`pip install wn`), download wordnets
   for en/pt/es/fr/it; export synsets to `Concept` rows (id =
   `c__{slug}__{hash[:12]}` from the ILI key, `definitions`, `lemmas`). Emit the
   matching `Lemma` rows and `Sense` edges straight from synset members. The ILI
   gives cross-lingual cognate grouping for free.
2. **Wiktionary enrichment** - pull per-language JSONL from kaikki.org
   (wiktextract) to fill sparse `definitions` and example fields, keyed by lemma
   and joined onto OMW synsets. Kept in a separate enrichment layer (license
   reasons - phase 10).
3. **LLM mapping/granularity** - use the LLM only to collapse WordNet's overly
   fine senses to learner-appropriate granularity and to disambiguate joins,
   verifiable against OMW - never as a primary data source.

## Cross-cutting concerns

- **Granularity** - start with WordNet synsets as-is; merge closely related
  senses or introduce a "concept cluster" layer if too fine (decided during this
  phase).
- **Idempotency & provenance** - re-runnable ingestion, each row tagged with its
  source for the dataset card and for maintenance (phase 8).
- **Scope** - target languages pt/fr/es/it/en only.

## Out of scope

- Frequency and CEFR values (phase 6) and semantic relations (phase 7), though
  the pipeline leaves hooks for both.
- Final sample-data selection and consumer wiring (phase 9); license finalization
  (phase 10).

## Done when (draft)

- Running the pipeline produces concepts/lemmas/senses for the five languages in
  the chosen format, loadable by the phase-4 store; spot-checks confirm
  cross-lingual grouping and gloss coverage.
- `uv run pytest && uv run ruff check . && uv run pyright` passes.
