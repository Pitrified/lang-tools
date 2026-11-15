---
status: planned
---

# Phase 1 - Measure the band re-cut

## Overview

The user chose to re-cut the CEFR bands (`00_start.md` Q3) because C2 holds 86% of acerta's
cards, common words included (hemorragia, zipf 3.57). The cutoffs were fitted against Kelly,
which grades only the 7,549 most frequent words, so the fit says nothing about where C2
should stop. This phase measures the options read-only and brings one to the user.
Context: [`00_start.md`](00_start.md).

## Goals

1. For each option, the band sizes per language (en, pt, it) and on acerta's cards, and the
   Kelly agreement (exact and within one band, en and it) against today's.
2. One recommendation, with the user's examples placed (hemorragia, cortisona, febre,
   pulmão, atelectasia, voluto).

## Plan

- Options to measure, over the built corpus with `cefr_validation`:
  - a. Higher upper cutoffs only: keep A1 to C1 as fitted, move the C1/C2 edge so C2 starts
    at a frequency, not at the end of Kelly's list.
  - b. Frequency quotas per language: each band a share of the language's lemmas by rank,
    so a band means the same depth in every language.
  - c. A band above C2 is not an option: CEFR has six bands and every consumer reads them.
- Each option keeps `cefr_is_estimated` everywhere and the quality gate's checks.
- Read-only: a notebook cell or a scratch script over `data/lexicon/`; no build.

## Out of scope

- Changing the score's terms or weights.

## Done when

- The numbers are in this file under "What the implementation found", and the user has
  picked an option (a new `Qn` in `00_start.md`).
