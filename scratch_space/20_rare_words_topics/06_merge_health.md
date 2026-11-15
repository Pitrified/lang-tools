---
status: done
---

# Phase 6 - Health folded into medical

## Overview

On acerta's settings screen two chips meant the same thing: Health (19 words, OMW's
`medicine` domain) and Medical (395, the hypernym roots and gloss tags). The user asked
for one. Context: [`00_start.md`](00_start.md).

## Plan

- `topics.json`: the `medicine` domain maps to `medical`; `health` leaves the vocabulary
  (no code in lang-tools or lang-tutor reads it).
- The 0.8.0 changelog entry says so, since 0.8.0 is not tagged yet.
- Rebuild (the user agreed, about 4.5 minutes), seed, `make check`, the quality report,
  the read API restarted; acerta re-exports.

## Done when

- `make check` passes; no concept carries `health`; the medical count is logged.

## What the implementation found

- Rebuilt with counts unchanged; 2,817 concepts carry `medical` (was 2,744 plus OMW's
  `medicine` domain), none `health`, 82,764 tagged as before; the seed did not move.
- The quality gate reads as before: the one known "definition == lemma" row.
- `make check` passes, 571 tests; the read API on 8010 restarted.
