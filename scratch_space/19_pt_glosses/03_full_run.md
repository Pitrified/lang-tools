---
status: draft
---

# Phase 3 - Full run and rebuild

## Overview

The remaining 42 batches, acceptance and the rebuild. Detailed once the pilot has reported.
Context: [`00_start.md`](00_start.md), depends on [`02_pilot.md`](02_pilot.md).

## Goals

1. Every pt concept with a pt word has a pt gloss.

## Plan

- Rounds of batches, a handful of subagents at a time, `CLI status` after each round, one
  commit per round of `gloss_backfill.jsonl` and the log.
- A sampled review (size set from the pilot's error rate), corrections by `CLI correct`.
- `accept_run(..., languages=["pt"])`, rebuild with `02_transform`, the quality gate: pt gloss
  coverage 100%.
- `docs/library/dataset_card.md`: the gloss counts and the known-gaps line.

## Out of scope

- es, fr, it.

## Done when

- The rebuild has no pt concept with a pt word and no pt gloss; `make check` passes.

## What the implementation found
