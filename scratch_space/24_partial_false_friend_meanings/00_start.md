---
status: draft
priority: 0
description: |
  Flag the partial false friends whose look-alike mainly means the meaning it shares with the pt
  word (it tardi "late" for pt tarde, which also means "late"), so acerta gives no decoy from them:
  a review of the partial en and it look-alikes of pt words that carry `means`.
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

## The idea, to be planned

- The worklist: each `partial` look-alike edge (pt word, en or it word) whose look-alike has `means`
  in the other known language; about 290 pairs as acerta reads them, more over the whole corpus.
- One question per pair: is what the look-alike mainly means (its best sense) a meaning of the pt
  word too?
- The result is a reviewed row per pair under `data/curated/`, re-applied by the build, and a field
  on `LookalikeHint` the export can honour (or `means` left empty for such a pair); a new tag, then
  an acerta re-export (acerta `plans/open_points.md`).
- The harness can follow `false_friend_meaning_review` (a gold set first, batches of 100).

Nothing is decided yet; the questions come when the folder is picked up.
