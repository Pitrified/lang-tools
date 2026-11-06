---
status: in progress
---

# Phase 2 - agent review

## Overview

One agent review of the pt top 1,000 cards and the 60 removed lemmas, a measured second review
of 500 targeted items (Q8), then apply. The labels are also the before table.
Context: [`00_start.md`](00_start.md), "Measurement", Q2 note, Q8. Depends on
[`01_tooling.md`](01_tooling.md).

## Plan

- Worklist: the 1,000 cards `12_card_senses` reviewed (same ids, so the counts compare); the 60
  lemmas that review removed are among them, served from their dropped links. Batches of 200
  (`m0001` to `m0005`), one subagent per batch.
- Gold for the new action (from phase 1): four unambiguous words just below the top 1,000 whose
  everyday meaning is not linked (*funcionário* "employee", *gatos* "cats", *turma* "class",
  *carreira* "career"), added to the gold file and recorded with `import-gold`, which now writes
  the addition a gold answer needs.
- The four gold verb forms (*homens*, *seja*, *tinha*, *olha*) had "no right card" as their
  answer, which Q1 a changes: their gold now names the base word's concept, and the corpus got
  the same fix through `add` with a form note. The gold file is now latest-row-wins per lemma,
  so the old answers stay as history.
- Measure the cost on the first batch and report it before the rest.
- First review `m0001` to `m0005`. Tally the causes from the labels and their reasons, not from
  a list fixed up front.
- Second review, blind, on 500 targeted items: every item the first review changes, filled with
  kept items. `agreement` over the two; at 90% or more on the changes, the first review's labels
  stand; below, the disagreements point at the rule to fix, which is fixed and the affected items
  served again.
- Write the measurement up as a repeatable method in `docs/guides/missing_senses.md` (the first
  meta-experiment on the review method, Q8), with what it found and what to try next.
- Apply; commit the curated files and the log.
- The second review came in at 69% on the changed items (`00_start.md` Q10): the rules were
  fixed (near misses, Q9's frequent reading, the twin tie-break, drops alongside an addition),
  `concepts` shows commonness, `agreement` counts twins apart, and the 53 disagreements are
  served again as `m0006` under the new rulebook. Phase 3's second review measures the fix.

## Out of scope

- es and fr (Q5).

## Done when

- Every item has an applied label; the before table (per action and cause), the same-rules
  agreement and the gold agreement are written here.

## What the implementation found
