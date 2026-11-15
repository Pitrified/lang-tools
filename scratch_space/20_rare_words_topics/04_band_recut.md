---
status: done
---

# Phase 4 - Re-cut the bands

## Overview

Applies option a of [`01_band_analysis.md`](01_band_analysis.md), the user's pick
(`00_start.md` Q4): for every language, C1 starts at score 0.50 and C2 at 0.60, so B2 now
runs from 0.4147 to 0.50; A1 to B1 keep their edges.
Context: [`00_start.md`](00_start.md).

## Goals

1. `CEFR_CUTOFFS = (0.2956, 0.3561, 0.4147, 0.50, 0.60)`.
2. The docs state the new agreement with Kelly and why the edges are no longer fitted.

## Plan

- `ingestion.enrich`: the two upper cutoffs, and the comment above them: the top two edges
  are set to bring common words out of C2, not fitted; English agreement is 29.1% exact,
  72.7% within one band, mean offset -0.50 (words called half a band easier than Kelly);
  Italian 33.1% / 76.1% / +0.56.
- `docs/library/lexicon.md` (CEFR) and `docs/library/dataset_card.md` (the band sizes, after
  the rebuild of phase 5).
- Tests that pin the cutoffs or a band edge updated.

## Out of scope

- Per-language cutoffs, the score's terms, unknown frequencies (an open point).

## Done when

- `make check` passes; the band sizes of the rebuild are logged in phase 5.

## What the implementation found

- No test pinned a band edge, so none changed; the 39 enrich and validation tests pass.
  A test restating the constant was not added.
