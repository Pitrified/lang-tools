---
status: done
---

# Phase 1 - `means` on the card's look-alikes

## Overview

Each look-alike on a card carries the words of its own main meaning in the card's other known
languages: it *bravo* on a pt card read with en and it known gives `means = {"en": [...]}`.
The main meaning is the look-alike lemma's best sense, the same pick its own card uses (a pin,
else frequency, then concept commonness), so this phase works before any review: one-sense words
are right at once, and the review of phases 2 to 4 only moves the pick for the others.
First because it is cheap, needs no review, and gives acerta a field to build against.
Context: [`00_start.md`](00_start.md).

## Current state

- `LookalikeHint` (`src/lang_tools/lexicon/card.py`): `language`, `text`, `kind`, `note`.
- `LexiconStore._card_lookalikes` (`lemma_store.py`) reads the edges of a page of cards in one
  query, joining the other lemma for its language and text.
- `lemma_drill` holds each lemma's best sense (`concept_id`); `_card_translations(concept_ids,
  languages)` gives a concept's words per language, lead first.

## Plan

1. `LookalikeHint.means: dict[str, list[str]] = {}`, documented as the words of the look-alike's
   best sense per known language other than its own; empty for a cognate (Q8).
2. `_card_lookalikes` also selects the other lemma's best-sense `concept_id` from `lemma_drill`,
   then one `_card_translations` call over those concepts for the query's known languages;
   each hint gets the languages other than its own, a language with no word left out.
3. `docs/library/frozen_api.md`: the field, "since v0.11.0"; the lexicon narrative on look-alikes.
4. Measured read-only on the current corpus (no rebuild needed: `lemma_drill` is derived when the
   store cache builds):
   false-friend hints on pt cards with a `means` in the other known language, per language;
   500 false-friend hints, from the most frequent pt cards down, read for whether the word is
   what the look-alike mainly means (the baseline the review should beat); the hint list is saved
   so phase 5 re-reads the same set.

## Tests

- `tests/lexicon/test_lemma_cards.py`, on the seed: a pt card's it false friend carries `means`
  in en from its best sense; a pinned best sense changes it; a cognate's `means` is empty;
  a look-alike whose best sense has no word in the other language has no key for it;
  the hint's own language is never a key.

## Out of scope

- The review (phases 2 to 4), the rebuild and release (phase 5).
- pt in `means`: pt is the card's language, and the notes already name the pt word.

## Done when

- `make check` passes; the baseline numbers and the 500-hint read are logged in `tracking.md`.

## What the implementation found

- The worklist and edge counts in `00_start.md` were read from the curated file; the built corpus
  has 973 full or partial edges and 847 known words, 664 of them with two or more senses
  (en 366, it 298). Corrected in `00_start.md`, `02_harness.md`, `04_full_run.md`.
- The baseline read is in [`01.1_baseline_read.md`](01.1_baseline_read.md): of 463 hints with a
  word, 42 wrong (en 5%, it 12%); 10 of the 42 are the right sense with a wrong first word.
