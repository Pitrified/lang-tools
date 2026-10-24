---
status: draft
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
  batches), and report traps per 100 pairs and per session point.
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
