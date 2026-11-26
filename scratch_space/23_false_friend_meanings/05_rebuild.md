---
status: done
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

## What the implementation found

- Rebuilt headless (`02_transform.ipynb`, output to the scratchpad), about 4 minutes. Corpus
  counts unchanged; `best_senses` applied 959 to 1,139 (the 180 pins), stale 1 to 1;
  `part_of_speech_changed` 116 to 127. The read API was not running, so nothing restarted.
- The 664 reviewed words: 180 own cards moved sense (one per pin), 11 changed part of speech,
  each the way the review meant (en *notice* to verb; *secure*, it *lucido* to adjective;
  *salt*, *fort*, *transit*, *compromise*, *delegate*, *surge*, *vest*, *advert* to noun).
  The quality report's part-of-speech table moves by exactly those 11; invariants PASS.
- Whole corpus hints: unchanged at 973; en hints with no it word 84 to 88.
- The same 500 hints re-read: right 421 to 455, wrong 42 to 9, empty 37 to 36.
  Of the 32 wrong-sense rows, 24 fixed, 2 now empty (en *lime*, *bravo*: the right sense has no
  it word), 6 left (it *sesta*, *redazione*, *tratto* are `m`; en *data* has one sense and is
  not on the worklist; it *prestazione* and en *nomination* were kept). Of the 10 lead-word
  rows, 7 fixed by the pick, 3 left (en *come*, *crusade*, it *gelateria*). No right row became
  wrong; 8 became empty (en *cult*, *sympathetic* x2, *post* x2, *disco*, *reunion*,
  *sympathy*), 11 empty rows gained a right word.
- The headless build refreshed the seed again (the `is_lead` field and more look-alike rows,
  as on 2026-11-22); restored to HEAD, seed unchanged.
- The dataset card's counts did not move; no edit. Version 0.11.0 with a changelog; no tag.
