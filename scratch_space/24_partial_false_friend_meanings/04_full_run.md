---
status: planned
---

# Phase 4 - The rest

## Overview

The other batches, `p0002` to `p0010`, as parallel subagents (the reservations are locked,
so two never get the same pair).
Context: [`00_start.md`](00_start.md) (Q5); depends on [`03_pilot.md`](03_pilot.md).

## Plan

- One subagent per batch, Sonnet at high effort (Q5), a handful at a time.
- `CLI status`; I read a random 100 labels; flagged edge cases re-checked where the read finds
  them wrong.
- Commit the log and the label files (`git add -f`).

## Done when

- Every worklist pair labelled; the counts per label and my read logged in `tracking.md`.
