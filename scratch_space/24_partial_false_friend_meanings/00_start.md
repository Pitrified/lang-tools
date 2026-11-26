---
status: in progress
priority: 0
description: |
  Flag the false friends whose look-alike mainly means a meaning it shares with the pt word
  (it tardi "late" for pt tarde, which also means "late"), so acerta gives no decoy from them:
  a review of the 973 full and partial en and it look-alikes of pt words, and a flag on the
  card's look-alikes.
depends_on: [23_false_friend_meanings]
comment: |
  Asked from acerta's plan 03_false_friend_rounds (its `00_start.md` Q19, answered d), on branch
  feat/03_false_friend_rounds of acerta-word-drills, 2026-11-26.
---

# Partial false-friend meanings - start

## Original note

acerta shows, in an English round, the English word for what an Italian false friend mainly means
(`LookalikeHint.means`, from `23_false_friend_meanings`): pt *bravo* "angry" gets *good* from
it *bravo*.
For a `partial` false friend that word is often a meaning the pt word shares with the look-alike,
so tapping it is not plainly wrong: pt *tarde* "afternoon" gets *late* from it *tardi*, and pt
*tarde* also means "late"; *quarto* "room" gets *fourth*; *reparar* "note" gets *repair*.
acerta read all 661 such decoys on the `v0.11.0` asset: 104 of the 290 from partial look-alikes
land on a shared meaning, against 1 of the 371 from full ones.
The app cannot tell these apart: checking the word against every meaning of the pt word catches
50 of the 104 and drops 37 good ones.
The user chose a review here (acerta `00_start.md` Q19, d).

## Current state

Read from the built `v0.11.0` corpus on 2026-11-26, read-only.

- 973 accepted false-friend edges between a pt word and an en or it word: 470 `full`, 503
  `partial` (251 en, 252 it).
  Of the partial ones, 448 have `means` in the other known language (196 en, all 252 it);
  the other 55 en look-alikes have a main sense with no it word.
- The edge (`LookalikeRelation`, the `lookalikes` table) carries `kind`, `similarity_score` and
  `explanation_notes`; `apply_lookalikes` builds it from `data/curated/lookalikes.jsonl`, latest
  row per pair.
  `LookalikeHint` (`lexicon/card.py`) is the card's view of it: `language`, `text`, `kind`,
  `note`, `means`; `_card_lookalikes` (`lemma_store.py`) fills it.
- `means` is the look-alike's best sense (`lemma_drill`), the pick folder 23 reviewed:
  180 en and it pins in `best_senses.jsonl`.
- The harness to copy is `false_friend_meaning_review` and its CLI, on `review_batches`
  (worklist, serve, apply, recheck, gold, status), with its rulebook, skill and gold file.
  Batch prefixes used in `data/curated/`: a to f, l, m, n, r, s, u, w; `p` is free.
- `CACHE_VERSION` is 11; the store rebuilds its SQLite cache when it changes.

### A mechanical check, measured and rejected

The corpus can say whether the look-alike's best concept is one of the pt word's senses: a
concept test, finer than acerta's word test.
On the 503 partial edges it says shared for 156.
Against acerta's 274 read partial decoys, it catches 38 of the 104 shared ones and flags 33 of
the 170 good ones, no better than the word test: a pt word's senses often miss the concept a
speaker would still use it for, or sit on a near one (it *tardi*'s main sense is "later than
usual or than expected"; pt *tarde* has "at an advanced age or stage" but not that one).
So the answer is a judgement about Portuguese usage, which is a review.

## The approach

- One review item per false-friend edge, partial or full (Q1): the pt word with its card meaning and senses, the en or it
  look-alike with the main meaning folder 23 settled (gloss and words), and the edge's note.
- One question: **does a Portuguese speaker use the pt word for the look-alike's main
  meaning?** Labels `s` (shared) or `d` (distinct), `!` for a judgement call, a reason after `#`.
- The labels go to a curated log, latest row per pair wins; the build sets a flag on the edge
  and the card's `LookalikeHint` carries it.
  The flag is a property of the pair, not of the answer language: the look-alike's main sense
  is the same whichever language its words are shown in.
  A full pair labelled `s` keeps its kind; it is listed in phase 5 as a candidate for a look-alike
  re-check, which is out of scope here.
- A third label, `w`: the main meaning shown is wrong; it sets no flag and lists the pair in the
  log for a later fix (Q3).
- What acerta does with the flag (no decoy from a flagged pair) is acerta's, in its
  `plans/open_points.md`; this folder ends at a release, `0.12.0`, tagged `v0.12.0` on the merge
  commit on `main` as `v0.11.0` was, when the user merges (Q6).

## Open questions

- Q1: Which edges go in the worklist?
  - a. All 503 partial edges.
  - b. The 448 partial edges whose look-alike has `means` in the other language, the only ones
    that give acerta a decoy today.
  - c. a, plus the 470 full edges.
  - Recommended: a, because the flag is a property of the pair and a later pin or added word can
    give the other 55 a `means`; they cost half a batch. c is not worth it: acerta found 1 shared
    meaning in 371 full decoys, and the look-alike rulebook gives `full` only to a pair with no
    everyday meaning in common.
  - ANS: c, all 503 partial and all 470 full pairs (the user, 2026-11-26): 973 items, 10 batches.
- Q2: Where does the flag live?
  - a. A new curated log, `shared_meaning_log.jsonl`, applied by the build onto a new edge field
    (`LookalikeRelation.shares_main_meaning`, a `lookalikes` column, `CACHE_VERSION` 12), shown as
    `LookalikeHint.shares_meaning: bool`, false by default.
  - b. No new field: the card leaves `means` empty for a flagged pair.
  - Recommended: a, because b mixes "this sense has no word" with "this meaning is shared", and
    acerta also reads `means` for the recap row, where a shared meaning is still worth showing.
    The new field is additive, so the frozen API change is a minor version.
  - ANS: a.
- Q3: A third label for a main meaning that is wrong?
  acerta's read found 41 decoys with a poor word or sense from lang-tools; folder 23 left 9
  wrong `means` rows open.
  - a. Yes: `w`, the main meaning shown is wrong, with a reason; it sets no flag and only lands
    in the log, as a list for a later fix.
  - b. No: two labels; the reviewer notes a wrong meaning after `#`.
  - Recommended: a, because it costs nothing in the review and turns a stray comment into a
    count the next folder can start from; the fix itself stays out of scope.
  - ANS: a.
- Q4: The gold set?
  - a. 30 pairs I label by hand from acerta's read (about 15 shared, 15 distinct, en and it both,
    with the hard ones: *tarde*, *quarto*, *reparar*), served first in the pilot; plus, as a
    measurement, the agreement with acerta's 274 read verdicts.
  - b. You label the 30.
  - Recommended: a, as in folder 23, where the 30 hand-labelled words were all matched; you can
    read the gold file before the pilot.
  - ANS: 50 gold pairs, labelled by me and used as they are, with no read by the user (the user, 2026-11-26).
- Q5: The review's model and cost.
  503 items are 6 batches of 100 (`p0001` to `p0006`); by folder 23's runs, about 80k tokens a
  batch, roughly 7 session points and 1 weekly point in all.
  - a. Sonnet at high effort for the pilot; if it matches fewer than 27 of the 30 gold pairs,
    the pilot is redone on Opus and Opus runs the rest.
  - b. Opus at high effort throughout.
  - Recommended: a, because the delegation ladder starts a bounded step on Sonnet and the gold
    set says whether it is enough; the redo costs one batch.
  - ANS: Sonnet at high effort (the user, 2026-11-26), for the pilot and the rest.
- Q6: The release.
  - a. 0.12.0 with a changelog entry and the frozen API line for `shares_meaning`; you tag it,
    and acerta's re-export follows on its side.
  - b. No release in this folder; the flag waits for the next one.
  - Recommended: a, because acerta is waiting for the flag and the field is additive.
  - ANS: a, and with a tag: `v0.12.0` (the user, 2026-11-26).
