---
status: done
---

# Phase 3 - review harness

## Overview

The agent review that produces the drops and the pins, built on the look-alike review's
harness. Context: [`00_start.md`](00_start.md); pt first (Q2, b), subagents (Q3, a).

## Plan

- **Shared plumbing:** the look-alike review's work-folder lock, row append, rulebook hash and
  label error move to `ingestion/review_batches.py`, and both reviews import them. The rest of
  the look-alike code (tiers, pairs, its gold) does not fit a lemma review and stays where it is.
- **Worklist** `data/curated/sense_worklist.jsonl`: the top 1,000 pt cards (es and fr later, Q2)
  in the cards' frequency order, single words, one-letter lemmas excluded (phase 1), gold lemmas
  left out. `CardQuery.limit` stops at 500, so the worklist reads pages, excluding the ids already
  taken.
- **Item:** the lemma, its part of speech, and each sense numbered in the card's pick order, so
  sense 1 is the current card; each sense with its gloss and top en translations. Every sense is
  shown (the pt top 500 hold up to 28), since a drop needs the sense on screen.
- **Label per item**, one line:
  - `N k`: the card is right;
  - `N p3`: pin sense 3;
  - `N d2,5 <reason>`: drop the wrong links 2 and 5, the card falls to the best sense left;
  - `N p3 d1 <reason>`: both;
  - `N x <reason>`: every link is wrong, the lemma leaves the corpus;
  - `!` after an action marks an edge case.
- **Rows:** every reviewed lemma gets a `BestSense` row (the pin, or no concept), which also marks
  it reviewed; each dropped sense gets a `FormDrop` row (kind `wrong link`) in
  `member_form_drops.jsonl`. Both accepted, tagged with the reviewer, the batch and the rulebook
  hash. `FormDrop` gains a `batch` field and `BestSense` an `edge_case` field, for a second look.
- **Rulebook** `docs/guides/sense_review.md`, its hash on every row; a skill
  `.claude/skills/sense-review/`.
- **Gold** `data/curated/sense_review_gold.jsonl`: each gold lemma lists the concept keys a right
  card may show (none: every link is wrong), and the agreement compares the card the reviewer's
  label leads to. Two per batch, reused once the pool runs out (seven items for five batches).
  From the lang-tutor reading, checked on the corpus: *homens*, *seja*, *tinha*, *olha* (every
  link wrong), *tarde*, *um*, *era* (a pin). *bem* is left out: its "rather" sense is a real
  reading, so the right card is a judgement call, not gold.
- CLI `sense_review_cli` with `worklist`, `import-gold`, `serve`, `apply`, `status`.

## Out of scope

- Retracting a drop: `apply_form_drops` applies every accepted drop row, so a later row cannot
  undo one. Not needed until a drop turns out wrong; the upgrade is latest-row-wins on the
  drop file, as for the look-alikes.
- es and fr worklists (phase 4, after pt).

## Done when

- One batch serves, applies and rebuilds end to end, as a test on a small built corpus, and a
  batch renders from the real corpus without reserving anything.
- `make check` passes.

## What the implementation found

- **The gold reading changed.** *homens* has one sense only (work force): the plural is not
  linked to *homem*'s concepts, so the right card does not exist and its gold is "every link
  wrong", not a pin. *tinha* "ringworm" is a real pt word, so it is gold only under the
  rare-homograph rule (`00_start.md` Q5).
- **The gold lemmas are also the rulebook's examples** (*seja*, *tinha*, *tarde*, *era*, *um*).
  That makes them easy to get right, so the gold measures drift and attention more than
  judgement. Enough for five batches; a larger, unseen gold set would be the upgrade if the
  agreement is ever in doubt.
- **The real corpus, dry run in a scratch data folder:** the pt worklist of 1,000 builds in 0.1 s
  (first *não*, *mais*, *também*; last *seguros*); every gold key exists; batch `s0001` serves
  200 cards and 2 gold, 429 senses, about 35k characters (roughly 10k tokens to read). The
  first lines already show the cases the review is for: *alguma* "in no manner", *jovens*
  linked to "juvenile person", *caso* "then" as sense 1.
- `make check` green (417, 5 new), docs build clean.
