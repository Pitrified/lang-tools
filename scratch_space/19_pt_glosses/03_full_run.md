---
status: planned
---

# Phase 3 - Full run and rebuild

## Overview

The remaining 42 batches, the sampled review, acceptance and the rebuild.
Context: [`00_start.md`](00_start.md), depends on [`02_pilot.md`](02_pilot.md).

## Goals

1. Every pt concept with a pt word has a pt gloss.

## Plan

- Rounds of batches, a handful of subagents at a time, `CLI status` after each round, one
  commit per round of `gloss_backfill.jsonl` and the log.
- Collect each subagent's `broken English` and `wrong pt words` lists (`00_start.md` Q8, Q10).
- Review a random 500 of the full-run glosses plus every `broken English` item (`00_start.md`
  Q9); corrections by `CLI correct`.
- Add the `wrong pt words` items, with the pilot's, to the `open_points.md` section on
  OpenWordnet-PT links, as a worklist for a later review.
- `accept_run(..., languages=["pt"])`, rebuild with `02_transform`, the quality gate: pt gloss
  coverage 100%.
- `docs/library/dataset_card.md`: the gloss counts and the known-gaps line.

## Out of scope

- es, fr, it.

## Done when

- The rebuild has no pt concept with a pt word and no pt gloss; `make check` passes.

## What the implementation found
