---
status: draft
---

# Phase 8 - maintenance (LLM-based)

> Draft. Scope sketch to hold the overarching story; not yet the plan of record.

## Overview

The dataset is not build-once: new lemmas arrive, glosses need filling, and
slug/sense quality drifts. This phase defines the ongoing, partly LLM-driven
upkeep loop that keeps the lexical graph healthy after the initial ingestion
(phase 5). Context: [`00-concepts-brainstorm.md`](00-concepts-brainstorm.md),
"Bootstrap source" (LLM mapping) and "Uplift plan". Reuses the ingestion
machinery rather than introducing a parallel path.

## What this phase will cover

- **New lemma -> concept mapping** - when a new lemma enters (e.g. from the
  `lemma_generator` or a user-supplied list), LLM-map it onto existing OMW
  synsets, creating a new `Concept` only when none fits; always verifiable against
  OMW to avoid hallucinated meanings.
- **Gloss / example enrichment** - fill sparse `definitions` and examples for
  under-covered languages, respecting the enrichment-layer license boundary
  (phase 10).
- **Slug dedup & integrity** - the pass that catches colliding `c__{slug}__...`
  ids that "should not exist in theory", plus orphaned senses, empty concepts,
  and asymmetric edges. Grounded by the first real en/pt build (2026-06-18), which
  produced a **considerable** number of shared slugs - a legibility issue only
  (the `hash[:12]` suffix keeps ids unique), driven by `_pick_slug_source`
  repeatedly falling back to the same English lemma / `"concept"`. See
  `05.2_perf_followups.md` (Observation 1) for the concrete trigger.
- **Validation against OMW** - periodic reconciliation so LLM edits do not drift
  from the ground-truth backbone; flag low-confidence/estimated entries for review.
- **Operational shape** - decide cadence and trigger (manual CLI vs scheduled
  job), and how runs are logged/auditable for the dataset card.

## Open points to resolve here

- How much autonomy the LLM gets (auto-apply vs propose-for-review).
- Where maintenance runs live (this repo's CLI? a scheduled agent?).
- Cost controls and batching for the LLM calls.

## Out of scope

- The initial bulk ingestion (phase 5); shipping/licensing mechanics (phase 10).

## Done when (draft)

- A documented, re-runnable maintenance entry point exists that maps a new lemma,
  enriches a sparse concept, and runs the integrity/dedup pass; dry-run output is
  reviewable.
- `uv run pytest && uv run ruff check . && uv run pyright` passes.
