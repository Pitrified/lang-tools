---
status: planned
---

# Phase 2 - Rulebook and harness

## Overview

The review tooling, copied from `false_friend_meaning_review`.
Linear after phase 1: `apply` writes the row model phase 1 defines.
Context: [`00_start.md`](00_start.md) (Q1, Q3, Q4); depends on
[`01_flag_on_cards.md`](01_flag_on_cards.md).

## Goals

1. `lexicon/ingestion/shared_meaning_review.py` and its CLI on `review_batches`: worklist,
   serve, apply, recheck, gold, status; batch prefix `p`, 100 items a batch.
2. The worklist: every full and partial edge between a pt word and an en or it word (973 on
   `v0.11.0`, Q1), gold first, then by the pt card's frequency; one item per pair, so a
   look-alike that is a false friend of two pt words is two items. An item names the edge's kind.
3. An item shows the pt word with its card gloss and its senses (gloss and en / it words), the
   look-alike with its main sense (gloss and words, the `means` folder 23 settled) and the edge's
   note.
4. The rulebook `docs/guides/shared_meaning_review.md` (in the nav): the question, the labels,
   the hard cases (a shared meaning that is rare in pt, regional use, a meaning shared only in a
   set phrase, a main sense on the wrong part of speech, a full pair that turns out shared, a
   main meaning that is itself wrong: `w`), the label format.
   Its hash is stored on every row.
5. The skill `.claude/skills/shared-meaning-review/`, as `false-friend-meaning-review`.
6. The gold file `data/curated/shared_meaning_gold.jsonl`, 50 pairs I label (Q4), used as
   they are: about 30 partial (half shared, with *tarde* / *tardi*, *quarto*, *reparar*) and 20
   full (with the one acerta found shared), en and it both, a few `w`; and `CLI gold`.

## Out of scope

- Running batches (phases 3 and 4).

## Done when

- Tests on a fixture for the worklist order, serve, apply (a bad label is refused with every
  problem listed), recheck and gold; `make check` passes; `make docs-build` is clean.
- `CLI worklist` on the built corpus lists the Q1 count, gold first.
