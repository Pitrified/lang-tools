---
status: in progress
---

# Phase 3 - tier depth

## Overview

Decide how far down the worklist the review goes, and with what, before spending the budget on
it. Tiers C to E hold 52,101 pairs: about 65 to 115 weekly points at the agent rates measured so
far, 450 to 800 pairs per point ([`00.1_usage_log.md`](00.1_usage_log.md)), so more than a
week's budget, and the false-friend rate falls with frequency. Context: [`00_start.md`](00_start.md), after
[`02_tier_b.md`](02_tier_b.md).

## Plan

- Measure the false-friend yield on one 200-pair sample each of tiers C, D and E (three agent
  batches), and report traps per 100 pairs and per session point. The samples are random
  (seeded `tier-C`, `tier-D`, `tier-E`) and stored as
  `data/work/lookalike_review/sample_tier_{c,d,e}.txt`, served with `recheck` as `c0001`,
  `d0001`, `e0001`: `serve` takes a tier's most common words first, so a served batch would
  overstate the tier's yield. The sampled rows count as reviewed and are not served again.
- Decide per tier between:
  - agents, as for tiers A and B;
  - a cheap-model verifier for the low tiers, with agents checking only its traps;
  - stopping, and leaving the rest as "neither" for the learner.
- If the verifier comes back, the parked work in phase 11 resumes from its files under
  `../09_concept_model/11_false_friends/`:
  - read the cache-probe result into `prompt_caching.md`;
  - add `cache_write_tokens` to `Usage`;
  - close or fold the parked verifier (#22) and cheap-model prompting (#26) into the decision.

## Out of scope

- Reviewing the tiers themselves: phase 4.

## Done when

- The three samples are applied and their yield is recorded here.
- Each of tiers C, D and E has a decided method or is dropped, with the reason.

## What the implementation found

The three random samples, applied on 2026-10-31 under guide `8c251b3ed4b0` (gold 14/15):

| Tier | Pairs | Traps (`f` + `p`) | Kept by the build | Pairs with known Zipf 3.3+ |
| ---- | ----: | ----------------: | ----------------: | -------------------------: |
| C    | 12,397 | 8 / 200 (4%) | 5 / 200 (2.5%) | 8,336 |
| D    | 17,490 | 2 / 200 (1%) | 2 / 200 (1%)   | 7,700 |
| E    | 22,214 | 2 / 200 (1%) | 0 / 200        | 7,968 |

- "Kept by the build" leaves out traps whose known word is under Zipf 3.3, which the build
  drops. Tier C's kept traps: *prejudicar* / *prejudice*, *signo* / *sign*, *massas* /
  *masses*, *exibido* / *exhibit*, *simpática* / *sympathetic*. Tier D's: *penico* / it
  *panico*, *crua* / *crude*. Tier E's two traps were both on rare known words.
- Since a trap on a rare known word never reaches the corpus, a tier can be filtered to the
  pairs whose known word is Zipf 3.3 or more before review, at no loss of traps; the cognates
  it skips are on words a learner does not know. That cuts C by a third and D and E by more
  than half.
- Sampling note: `recheck` mixes gold pairs in without excluding the batch's own keys, so a
  sampled pair that is also in the gold set is served twice (*derelito* / *decrepit* in
  `e0001`); only one row is written, so nothing is double counted.

### Samples extended to 1,000 pairs per tier

On the user's request the samples grew to 1,000 random pairs per tier (800 more each, seeded
`tier-C-2` and so on, appended to the same key files; `c0002` to `c0005`, `d0002` to `d0005`,
`e0002` to `e0005`). Gold 68/75. Rates with a 95% interval:

| Tier | Traps | Kept by the build | Kept rate | Pairs with known Zipf 3.3+ in the sample | Kept rate among them | Pairs left after the filter | Expected kept traps |
| ---- | ----: | ----: | ----: | ----: | ----: | ----: | ----: |
| C | 40 | 32 | 3.2% ± 1.1 | 681 | 4.7% ± 1.6 | about 7,650 | about 360 |
| D | 17 | 12 | 1.2% ± 0.7 | 436 | 2.8% ± 1.5 | about 7,260 | about 200 |
| E | 14 | 7  | 0.7% ± 0.5 | 370 | 1.9% ± 1.4 | about 7,600 | about 140 |

- "Pairs left" is the filtered tier minus the sampled pairs that passed the filter.
- At about 600 pairs per weekly point, each filtered tier costs about 13 weekly points:
  about 28 kept traps per weekly point in C, 17 in D, 11 in E.
- The 200-pair samples had read C at 2.5% and E at 0; the larger samples put C higher and
  show E is not empty, but it stays the lowest.
