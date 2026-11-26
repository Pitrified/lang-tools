---
status: done
---

# Phase 4 - The rest

## Overview

The remaining words (564 after the pilot, 6 batches), in parallel, with a usage reading after.
Context: [`03_pilot.md`](03_pilot.md).

## Plan

- Serve and run the batches in parallel subagents; apply each.
- My read of a random 100 across the batches; re-check batches for what it finds.
- Labels per batch and the edge cases logged.

## Done when

- Every worklist word has a row; `status` shows none left; the read and the usage are logged.

## What the implementation found

- Six batches, `f0002` to `f0007`, served at the same time by six subagents: five got 100 words,
  `f0002`, reserving last, got the remaining 64. Every batch applied on the first try.
- Labels over all 664: 470 `k`, 180 `p`, 14 `m`; gold still 30/30.
  Per batch (k / p / m / edge): f0002 43/21/0/16, f0003 77/20/3/22, f0004 64/34/2/27,
  f0005 78/19/3/21, f0006 67/31/2/30, f0007 67/31/2/24.
- The `m` words are mostly a modern meaning WordNet lacks (it *sito* website, *navigatore* satnav,
  *patente* driving licence; en *amazon*, *scout*) or an ordinal or participle (it *terza*,
  *quinta*, *sesta*, *vinto*).
- My read of a seeded random 100 across f0002 to f0007: all acceptable. Three are nearest-sense
  pins where the main meaning has no sense of its own (en *post* "publicize with a poster" for
  posting online, it *incidere* "engrave", it *cappa* "cloak"); the rulebook asks `m` only when
  no listed sense is the main meaning, and each of these is a main meaning too. No re-check.
- Each subagent took 67k to 85k tokens and 65 to 91 seconds.
