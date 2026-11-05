---
status: done
---

# Phase 4 - review run

## Overview

Run the review over the worklist, rebuild, and hand the result to lang-tutor's phase 3 for the
re-listing. Context: [`00_start.md`](00_start.md).

## Plan

- One measured batch first, its cost reported, before the rest (`00_start.md` Q3).
- pt first; es and fr only after the pt round goes well (Q2, b).
- Rounds of 200-card batches, one commit per round, a rebuild and the gate after each round.
- Re-list the top 500 per language and count the bad cards again.

## Done when

- Every worklist card has a reviewed row; the rebuild passes the gate.
- The re-listed top 500 pt show no wrong best sense, or the ones left are listed with the reason.

## What the implementation found

- **The pt round** (2026-11-04 and 05): five batches of 200, one measured first (about 66k
  tokens, 126 s), then four in parallel (about 70k tokens each, under two minutes). About 345k
  tokens for the 1,000 cards, far under the 2 to 3 weekly points guessed in `00_start.md` Q3.
  806 kept, 102 pinned, 106 senses and 61 lemmas dropped, 64 edge cases, gold 9/9.
- **Rebuild and gate:** 105 pins applied (102 plus the three gold pins), 0 stale, 265 senses
  dropped by the member-form stage; gate PASS. The committed seed changes only by the new
  `is_best` field (one pin in it, *a lot*).
- **Re-listed top 500 pt:** about 16 cards still doubtful, against about 98 before:
  - no right sense in the corpus, kept by the reviewer since the linked one is not plainly
    wrong: *sim* (gloss "not only so, but"), *além* "yonder", *última* "latter", *seis* (the
    playing card), *partes* "the local environment", *nomes* "epithet", *irmãos* "brethren",
    *índia* "Indian", *natal* (no "Christmas"); adding the missing links is a different job
    than this review;
  - homographs of verb forms kept under the rulebook's "ordinary use" rule: *são* "healthy",
    *passa* "raisin", *leva* "horde", *precisa*, *preciso* "precise", *vão* "vain";
  - one reviewer miss: *copa* "crown of a hat", where "a drinking glass" was the better pin.
- **Drops worth a human look** (the lemma left the corpus): *vinte*, *mano*, *moderna*,
  *cura*, *campeonato*, *destaque*, *terras*, *brasil*, *pernambuco*. A drop row cannot be
  retracted yet (phase 3, out of scope).
- **es and fr not run** (`00_start.md` Q6): the phase closes on pt. The drop retraction and
  the *copa* repin are phase 5; the missing senses a sibling folder (Q8).
