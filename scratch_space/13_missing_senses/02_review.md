---
status: draft
---

# Phase 2 - agent review

## Overview

One agent review of the pt top 1,000 cards and the 60 removed lemmas, a measured second review
of 500 targeted items (Q8), then apply. The labels are also the before table.
Context: [`00_start.md`](00_start.md), "Measurement", Q2 note, Q8. Depends on
[`01_tooling.md`](01_tooling.md).

## Plan

- Worklist: the 1,000 cards `12_card_senses` reviewed (same ids, so the counts compare) plus
  the 60 removed lemmas; batches of 200, ids reserved up front, one subagent per batch.
- Measure the cost on the first batch and report it before the rest.
- First review `m0001` to `m0006`. Tally the causes from the labels and their reasons, not from
  a list fixed up front.
- Second review, blind, on 500 targeted items: every item the first review changes, filled with
  kept items. `agreement` over the two; at 90% or more on the changes, the first review's labels
  stand; below, the disagreements point at the rule to fix, which is fixed and the affected items
  served again.
- Write the measurement up as a repeatable method in `docs/guides/missing_senses.md` (the first
  meta-experiment on the review method, Q8), with what it found and what to try next.
- Apply; commit the curated files and the log.

## Out of scope

- es and fr (Q5).

## Done when

- Every item has an applied label; the before table (per action and cause), the same-rules
  agreement and the gold agreement are written here.

## What the implementation found
