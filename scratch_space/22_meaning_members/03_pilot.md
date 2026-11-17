---
status: done
---

# Phase 3 - Pilot of 500+

## Overview

Run the review on a pilot and read it before the rest.
Context: [`00_start.md`](00_start.md), depends on [`02_harness.md`](02_harness.md).

## Goals

1. Five meaning batches of 100 meanings (`w0002` to `w0006`, the worklist's order is a hash,
   so they are a fair sample of the levels and the hints), and the 202 remaining lead meanings
   (`l0002` to `l0004`).
2. Per-verdict counts, and an agreement check on a hand-read sample of each kind.
3. The usage read by the user after the pilot, to size the waves of phase 4.

## Done when

- The counts and the agreement are logged, and the rulebook is fixed where the sample shows it
  wrong, with a re-label of the affected batches.

## What the implementation found

- Counts, w0002 to w0006 (500 meanings, 1,393 words): 1,269 k, 28 f, 96 d. Leads l0002 to
  l0004 (202 meanings, all 207 with the smoke batch): 123 k, 84 l. Each subagent took about
  35 s and 55k tokens for a meaning batch, 20 s and 45k for a lead batch.
- Hand-read: every f (28, all right), every d (96, about 92% right), 25 meanings of k (70 words,
  about 95% right), 35 leads (about 95% right).
- The wrong drops had one cause: a word dropped for its usual meaning when it also has the
  meaning's (*silencioso*, also a car's silencer; *macio*, also smooth; *vida*, also
  liveliness; *terrivelmente*, also "fearfully"), and near words (*pedra* on pebble,
  *sepultura* on burial). The wrong keeps were spellings (*forgoso* for *fogoso*, *gripa*).
  The rulebook got three rules for these, and a fourth after the re-check, on pre-1990 hyphens
  and accents.
- A `recheck` command was added (phase 2 had left it out until a case): it serves again the
  reviewed meanings with a given label and undoes an old drop or form. Re-check w9001 served
  the 85 meanings with a drop (257 words) and changed 28 labels: the wrong drops above came
  back, and a few new drops are right (*furor* on liveliness, *lutador* on "defiantly
  aggressive", *informável*). *índio* stays dropped: that meaning is thallium.
- Left as labelled: the pilot's keeps were not re-read under the spelling rule, and the
  re-check kept *auto-estima*, *mini-saia* and *ultra-som* before the hyphen rule existed.
