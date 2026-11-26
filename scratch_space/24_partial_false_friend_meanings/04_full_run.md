---
status: done
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

## What the implementation found

- `p0002` to `p0010` (873 pairs; `p0010` the last 73), nine Sonnet subagents at high effort, five
  then four at a time, 69k to 89k tokens and 54 to 102 s each; no batch needed a second apply.
- All 973 labelled: 293 `s`, 665 `d`, 15 `w`, 194 edge cases. Partial pairs: 269 `s`, 222 `d`,
  12 `w`; full pairs: 24 `s`, 443 `d`, 3 `w`. `s` by look-alike language: 160 en, 133 it.
- My read of a random 100 from `p0002` to `p0010`: 2 wrong (pt *firmar* / it *firma* `s!`, the
  verb read as the noun "signature"; pt *deposição* / it *deposizione* `s!`, testimony is
  *depoimento*), several debatable but defensible (*prestar* "lend", *balcão* "balcony",
  *morsa* "vise", BR anglicisms such as *realizar* "realise"). Re-checked as `p9001` with the
  `p0009` `w!` on it *coda* (queue is a main meaning): all three `d`. The `p9001` rows carry
  `model` `agent-review`, though I labelled them.
- Side findings, out of scope: the learner note on pt *bruto* / it *bruto* says it *bruto* means
  ugly, which `p0006` read as wrong; the 24 full pairs labelled `s` are candidates for a
  look-alike re-check (phase 5 lists them).
