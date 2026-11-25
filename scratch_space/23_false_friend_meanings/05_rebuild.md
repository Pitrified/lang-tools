---
status: draft
---

# Phase 5 - Rebuild and release

## Overview

The pins reach the corpus, the cards and acerta.
Context: [`00_start.md`](00_start.md); acerta's side is its plan `03_false_friend_rounds`,
phase 4 (on acerta-word-drills, branch `feat/03_false_friend_rounds`).

## Plan

- Agree the rebuild with the user (about 4.5 minutes, the read API restarted).
- Before and after:
  - best-sense pins applied and stale;
  - false-friend hints with a `means` per language, and how many changed word;
  - lemmas whose part of speech the pins changed (`apply_pinned_part_of_speech`, Q6);
  - the same 500 hints as phase 1, read again.
- Seed, quality report, dataset card; version 0.11.0 with a changelog (the `means` field and the
  pins); no tag (the user's, with the push).
- Tell acerta's plan the tag is ready; the re-export is acerta's phase 4.

## Done when

- `make check` passes; the numbers are logged; the user has them.
