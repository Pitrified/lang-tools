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

> **From phase 5.55 (2026-07-11).** The slug **tier-2 qualifier job is this phase's
> first real LLM task**: LLM-pick a 1-3 word gloss-derived qualifier for each of the
> ~9,782 same-lexfile collision groups (~23,476 concepts) left after 5.55's
> deterministic lexfile tier. Decisions already made: the reviewed qualifier table is a
> **committed build input** (small JSONL in normal git, keyed by ILI grouping key), and
> the job runs through the **Batch API** (-50%); sized at ~1.5M in / ~0.3M out tokens ≈
> $1.50 (Haiku) to $7.50 (Opus) - cost does not constrain the model choice. Spec in
> [`05.55_llm_cleanup/05.55_llm_cleanup.md`](05.55_llm_cleanup/05.55_llm_cleanup.md).

> **From phase 6 (2026-09-02).** The **LLM CEFR judgment for pt/es/fr** is routed here.
> Those three languages have no graded list, so phase 6 ships them the same deterministic
> band as everyone else and stops there: with no ground truth, no measurement separates a
> better estimate from a different one, which is precisely why the refinement needs this
> phase's human-in-the-loop review rather than an unreviewed pass. The shape is already
> fixed by 05.58 - accepted judgments become a committed `cefr_overrides.jsonl` the build
> applies, the same contract as `gloss_overrides.jsonl` - and by 5.55's Batch API decision.
> It is concept-level (117,659 concepts), not per-sense. Read phase 6's fitted band
> distributions first; they say whether the deterministic estimate needs help at all.

> **From phase 6 (2026-09-02).** Member-form quality, continued from 5.57: 7.8% of the
> English senses banded A1 are forms of two characters or fewer, including roman numerals
> (`II`). They are legitimate high-frequency OMW members, so this is a review question
> rather than a token rule, and it joins 5.57's deferred items (French sense spread, the
> ~150 sentence-like non-en forms).

> **From the 5.5 cleanup (2026-06-20).** Steps 5-6 of
> [`05.5_cleanup.md`](05.5_cleanup.md) are this phase's concrete first run over the
> kaikki-free rebuild: slug dedup, `definition == lemma` repair, orphan / empty-concept
> review, OMW-internal POS review, and an optional license-clean LLM gloss backfill, then
> re-running the 05.4 check harness as a regression gate. The LLM stays propose-for-review
> for anything that changes meaning, auto-apply only for mechanical slug fixes.

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
  and asymmetric edges. Grounded by the first real en/pt build (2026-06-17), which
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
