---
status: planned
---

# Phase 3 - review harness

## Overview

The agent review that produces the drops and the pins, built on the look-alike review's
harness. Context: [`00_start.md`](00_start.md); pt first (Q2, b), subagents (Q3, a).

## Plan

- **Worklist:** the top 1,000 pt cards (es and fr later, Q2) in frequency order, single words, one-letter
  lemmas excluded (phase 1).
- **Item:** the lemma, its frequency rank, and each sense with its gloss and top translations,
  the current pick marked.
- **Label per item:** keep the pick; pin sense *k*; drop the links that are wrong (a list of
  senses); drop every link (no right sense, so the lemma leaves the corpus). Drops go to
  `member_form_drops.jsonl`, pins to `best_senses.jsonl`.
- **Rulebook** `docs/guides/sense_review.md`, its hash on every row; a skill
  `.claude/skills/sense-review/`; hidden gold items from the phase 3 reading in lang-tutor
  (*homens*, *seja*, *bem*, *era*).
- CLI subcommands `serve`, `apply`, `status`, reusing the look-alike review's batch and gold
  code where it fits rather than copying it.

## Done when

- One batch serves, applies and rebuilds end to end on a dry run.
- `make check` passes.
