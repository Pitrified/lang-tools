---
status: planned
---

# Phase 3 - Pilot

## Overview

One batch, `p0001`, with the gold pairs first, to test the rulebook before the rest.
Context: [`00_start.md`](00_start.md) (Q4, Q5); depends on [`02_harness.md`](02_harness.md).

## Plan

- A subagent follows the skill for `p0001` on Sonnet at high effort (Q5).
- `CLI gold`; then I read the 50 other labels against the rulebook, and the overlap with
  acerta's read verdicts (`shared` against `s`, `good` against `d`).
- A rulebook change, if the read calls for one, is made before phase 4 and the pilot re-checked.

## Done when

- Gold agreement and my read logged in `tracking.md`.
- Below 45 of the 50 gold pairs, or a read that finds the rulebook unclear, the loop stops and
  asks before phase 4: Q5 settled the model, so a change to it is the user's.
