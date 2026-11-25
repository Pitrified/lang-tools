# implementation tracking

What a false friend's look-alike mainly means, as data: a reviewed best-sense pin on each en or
it word that is a full or partial false friend of a pt word, and a `means` field on the card's
look-alikes with that meaning's words in the other known language.
For acerta's cross-language decoys (pt *bravo* "angry", it *bravo* "good": *good* is the trap
in an English round). Analysis and decisions in [`00_start.md`](00_start.md).

## Key decisions

- The main meaning is a property of the known word, so it is a best-sense pin on that word in
  `best_senses.jsonl`, not a field of the look-alike row.
- Its own review, rulebook and skill (Q1); en and it words with two or more senses, 664 on the built corpus (Q3);
  one-sense words need no row.
- No translation written where the main sense has none in the other language (Q2).
- `means` comes from the look-alike's best sense, the same pick as its own card, so the field
  works before the review and the review only moves the pick.
- The pins are ordinary best-sense pins: they also set the word's part of speech and its own
  card sense; phase 5 counts those changes (Q6).
- `means` lands first, then the review (Q7); it is filled on full and partial false friends only,
  empty on cognates (Q8); batches are `f0001` and up (Q9).
- The baseline read is 500 false-friend hints from the most frequent pt cards, re-read on the
  same set after the rebuild.

## Phases

| #  | Phase                       | Plan                                         | Status |
| -- | --------------------------- | -------------------------------------------- | ------ |
| 1  | `means` on the cards        | [`01_means_on_cards.md`](01_means_on_cards.md) | done |
| 2  | Rulebook and harness        | [`02_harness.md`](02_harness.md)             | draft  |
| 3  | Pilot                       | [`03_pilot.md`](03_pilot.md)                 | draft  |
| 4  | The rest                    | [`04_full_run.md`](04_full_run.md)           | draft  |
| 5  | Rebuild and release         | [`05_rebuild.md`](05_rebuild.md)             | draft  |

Status values: draft / planned / in progress / done / superseded / discarded.

## Log

Append-only. Newest at the bottom.

- 2026-11-25 : bootstrapped from acerta's `03_false_friend_rounds` Q10 (acerta-word-drills,
  branch `feat/03_false_friend_rounds`), on branch `feat/23_false_friend_meanings` from `main`
  (`3aa3528`); 23 free on every ref. Measured read-only: 1,230 accepted full and partial edges,
  1,085 known words, 798 with two or more senses (en 453, it 345); it senses tie on frequency;
  67 en words have no sense with an it word. Q1 to Q5 answered (own review, no new translations,
  en reviewed too, about 10 session points fine, no re-run of the sense reviews).
- 2026-11-25 : phases written. Read for them: `best_senses.py` (pins keyed on lemma and
  `concept_key`, latest row wins, any language; `apply_pinned_part_of_speech` also sets a pinned
  word's part of speech, raised as Q6), `lemma_drill` (best sense: pin, frequency, commonness),
  `_card_lookalikes` (one query per page of cards), `review_batches` and `unranked_review` (the
  harness to copy). Batch prefix `f` is unused across `data/curated/`. Q6 to Q9 raised.
- 2026-11-25 : Q6 to Q9 answered, all recommendations (pins as ordinary best-sense pins, `means`
  first, false friends only, prefix `f`); folded in. Baseline read in phases 1 and 5 resized from
  50 to 500 targeted hints, per the standing 500-item rule for before/after assessments.
- 2026-11-25 : phase 1 done. `LookalikeHint.means` from the look-alike's `lemma_drill` best
  sense, one more batched `_card_translations` read; tests on a pt *bravo* fixture (it full,
  en partial, a no-word sense, a pin, a cognate); `frozen_api.md` and `lexicon.md` updated;
  `make check` 603 passed. Measured: 836 pt trap cards, 973 hints; 84 en hints have no it word.
  The 500-hint read (`01.1_baseline_read.md`): 421 right, 42 wrong (en 12, it 30), 37 empty;
  32 wrong sense, 10 right sense with a wrong first word. Counts in `00_start.md` corrected from
  the curated file (1,230 edges, 798 words) to the built corpus (973 edges, 664 words).
