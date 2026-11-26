---
status: done
---

# Phase 2 - Rulebook and harness

## Overview

A review of its own (`00_start.md` Q1): for each en or it word that is a full or partial false
friend of a pt word and has two or more senses, pick the sense a speaker of that language means
first today. Rows are best-sense pins on that word, in the existing pin file.
Context: [`00_start.md`](00_start.md); built like `21_unranked_pt_words` (on `main`).

## Plan

1. Rulebook `docs/guides/false_friend_meaning_review.md`: the question, the label format, the hard
   cases (a word whose main sense is the one it shares with the pt word, as it *novella* "short
   story": pick it anyway, the pick is about the word, not the pair; a register or regional split;
   a sense list missing the main meaning: `none`, flagged).
   Its hash goes on every row (`review_batches.guide_sha`).
2. `src/lang_tools/lexicon/ingestion/false_friend_meaning_review.py` and a `_cli.py`, on
   `review_batches` like `unranked_review`:
   - worklist: the known lemmas of the accepted full and partial edges with two or more senses
     (664 on the built corpus: en 366, it 298), the most frequent first;
   - a batch item: the word, its language, its senses numbered (gloss, words in en / it / pt,
     frequency where the language has one), and the pt words it is a false friend of with their
     notes, which often name the main meaning already;
   - labels: `k` (sense 1, the current pick), `pK` (pin sense K), `m` (the main meaning is not
     listed; needs a reason), each with an optional `!` edge-case flag;
   - apply: `BestSense` rows to `data/curated/best_senses.jsonl` (`concept_key` of the picked
     sense, `batch` with the review's own prefix, Q9) and a review log of its own;
   - `status`: reviewed, pending, left.
3. Skill `.claude/skills/false-friend-meaning-review/SKILL.md`, as the unranked one: serve a batch,
   label, apply, report.
4. A gold set of 30 words labelled by hand (mixed en / it, a few hard cases), as the other reviews
   have, to measure a batch against.

## Tests

- Worklist: one-sense words left out, cognate-only words left out, a word false friend of two pt
  words listed once.
- Labels: a number out of range, a missing word, a duplicate are `LabelError`s.
- Apply: a pin row per labelled word, `none` writes a row with no concept (retracts an earlier
  pin), a re-applied batch is refused; a pin is picked up by `apply_best_senses` and moves the
  word's card sense (seed).

## Out of scope

- Running batches (phases 3 and 4).
- Writing missing translations (`00_start.md` Q2).

## Done when

- `make check` passes; the worklist is built and its size logged; the gold set is committed.

## What the implementation found

- Labels follow the card-sense review's `k` / `pK` rather than a bare number: `k` and `m` write a
  `BestSense` row with no concept, like the sense review's keep, and the log row records the
  chosen concept (sense 1 for `k`), which the gold comparison reads.
- The gold lemmas go first in the worklist instead of being mixed in hidden, so the pilot batch
  (phase 3) carries all 30, unmarked; `gold` compares their latest labels.
- A re-check names words as `language:text`: en and it share spellings (*bravo*).
- The sense review's re-check and reviewed set read `best_senses.jsonl` too, but only for lemmas
  on its own (pt) worklist, so the en and it rows here do not reach it.
- The gold set: 17 it and 13 en words, 10 of them right at sense 1; several accept two or three
  senses where both are the main meaning (it *scala* stairs or ladder, en *time*).
  en *bravo* and en *lime* have their main sense listed with no it word, so after the review
  their `means` stays empty: a pin cannot add words.
- Worklist built with the CLI: 664 lemmas, gold first.
