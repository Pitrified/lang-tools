---
status: planned
---

# Phase 3 - curated concepts

## Overview

A curated input that creates a concept the sources lack, so phase 4 can link the modals.
Context: [`00_start.md`](00_start.md) Q2, Q3.

## Plan

- `data/curated/concept_additions.jsonl`, one row per concept, latest row wins per source key:
  `source_key` (`manual:can-be-able`), `slug`, `lexfile` (the nearest WordNet class,
  `verb.social` or `verb.cognition`), `definition` (en), `members` (en), and the provenance
  fields `sense_additions.jsonl` rows carry.
- A module `ingestion/concept_additions.py` beside `sense_additions.py`, with
  `load_concept_additions` and `apply_concept_additions`. The concept id is
  `concept_id(slug, source_key)`, so its key is stable; the en members become en lemmas and
  senses as in `transform`; `definition_sources` tagged `manual`.
- The build stage goes right before `apply_sense_additions` in `pipeline.build_initial`, so an
  addition can link to it, with its counts in `_build.json`.
- A row whose slug or key collides with a source concept is counted stale and skipped.
- Read before writing: how `transform` builds concepts, members and senses; what the gate,
  `commonness`, CEFR and topics expect of a concept with no ILI (none of them may crash or flag
  it); what the look-alike and gloss stages do with it. Findings here.
- Tests on the bootstrap seed: a row creates the concept and its en lemma, an addition links a
  pt lemma to it, a later retracting row removes it, a colliding row is stale.
- `docs/library/` (the build narrative) and `docs/guides/rebuild_corpus.md` gain the input.
- The two concepts of Q3 a: "be able to, can, may" (en *can*, *be able to*, *may*) and "must,
  have to, be obliged to" (en *must*, *have to*). The en *can* and *must* lemmas already exist
  (tin can, grape must), so the rows link the new senses to them.

## Out of scope

- The pt links: phase 4.
- Concepts for any other gap (phase 1's follow-ups).

## Done when

- The input, its stage, tests and docs are in; `make check` passes; a rebuild holds the two
  concepts with their en members and the gate passes.
