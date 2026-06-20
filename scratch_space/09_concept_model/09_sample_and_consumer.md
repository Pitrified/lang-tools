---
status: draft
---

# Phase 9 - sample data + consumer uplift

> Draft. Scope sketch to hold the overarching story; not yet the plan of record.

## Overview

Replace the disposable ~50-word bootstrap sample with fresh sample data produced
by the new pipeline, and point the store and `lang-tutor` at it. This is the
"no migration" decision made real: we regenerate rather than backfill. Context:
[`00-concepts-brainstorm.md`](00-concepts-brainstorm.md), "Uplift plan (no data
migration)". Depends on phases 2-7 being far enough along to emit a coherent
slice.

> **From the 5.5 cleanup (2026-06-20).** Regenerate the sample slice from the kaikki-free
> rebuild (Step 6 of [`05.5_cleanup.md`](05.5_cleanup.md)); the carve must stay
> referentially closed (no dangling edges, no lemma without a sense).

## What this phase will cover

- **Sample selection** - a small, curated slice from the phase-5 pipeline: a
  handful of concepts with their cross-lingual lemmas and senses, a few
  false-friend and relation edges, and frequency/CEFR values - enough to exercise
  every model feature and every exercise type, kept tiny for fast tests.
- **Replace bootstrap files** - regenerate `data/bootstrap/` (or its successor
  layout from phase 3) in the new format; remove the old flat CSV shape.
- **Point the store** - `lemma_store` loads the new sample by default.
- **`lang-tutor` uplift** - since it moves in lockstep and only needs a lemma
  list, confirm it still selects/drills correctly on the new data; opportunistically
  let it consume the new signals (synonym drills from `Concept.lemmas`,
  false-friend traps, frequency/CEFR ordering) if cheap, else defer to its own
  backlog.
- **End-to-end check** - producer webapp serves the new `/api/v1/lemmas` +
  concept endpoints; `lang-tutor` runs a full exercise round against them.

## Out of scope

- The full production dataset (this is the sample); license packaging (phase 10).
- New `lang-tutor` exercise types (its own roadmap) beyond verifying the contract.

## Done when (draft)

- Fresh sample data ships and loads; the old flat bootstrap is gone; both repos'
  verification suites pass against it.
- A manual end-to-end run (or `/verify`) shows `lang-tutor` drilling on the new
  data with no regressions.
