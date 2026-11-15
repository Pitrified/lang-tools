---
status: done
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

## What the implementation found

Kelly en (7,549 rows) and it (6,865) were downloaded and staged with
`staging.cefr.download_cefr_source` on 2026-11-15, validation-only as before.
Scores recomputed read-only over the 2026-11-13 build; acerta's cards are the 29,376 pt
cards of its asset, "floored" the 18,214 with lemma zipf 2.0 or more.

| Option | Cutoffs | en exact / within 1 / offset | it exact / within 1 / offset | acerta floored C2 |
| ------ | ------- | ---------------------------- | ---------------------------- | ----------------- |
| today | .2956 .3561 .4147 .4499 .4813 | 42.1% / 74.0% / -0.01 | 22.9% / 63.7% / +1.06 | 79% |
| a. upper edges up | ... .4147 .50 .60 | 29.1% / 72.7% / -0.50 | 33.1% / 76.1% / +0.56 | 45% |
| b. rank quotas per language | by rank | - | - | 82% |
| c. it-fitted, all but en | .3548 .4171 .4596 .5111 .6108 | unchanged (en keeps today's) | 38.3% / 78.9% / 0.00 | 41% |

- b makes pt worse: pt has fewer lemmas than en, so a fixed quota reaches further down.
- a moves the user's examples the right way but costs English 13 points of exact agreement
  and calls English words half a band too easy.
- c fits the Italian cutoffs on Italian Kelly, the way the English ones were fitted on
  English Kelly, and uses them for the languages with no graded list of their own
  (pt, es, fr), on the assumption that they sit closer to Italian than to English; with
  no graded list for them, that is not measured.
  The current doc already names the reused English cutoffs as the cause of Italian's +1.05
  offset. Rank correlation is unchanged (en 0.636, it 0.658): only the cut moves.
- Under c, acerta's floored cards are A1 5%, A2 6%, B1 6%, B2 11%, C1 31%, C2 41%;
  the examples: doença A2, agência A2, equipe A1, febre / pulmão / fígado B2,
  hemorragia / insulina C1, cortisona / aspirina / atelectasia C2.
- voluto (no pt frequency) is C1 today and B2 under c: an unknown frequency scores as
  mid-scale (`enrich.NEUTRAL`), not as rare. 8,597 of 63,692 pt lemmas have no frequency.
  Scoring an unknown frequency as the zipf floor moves voluto to C2 and grows C2 again
  (pt lemmas C2 45% to 56% under a). The commonness floor keeps them out of acerta either
  way; for the corpus it is `00_start.md` Q5.
