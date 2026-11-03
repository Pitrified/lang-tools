---
status: planned
---

# Phase 2 - override input

## Overview

A reviewed best sense has to reach the drill table. Add the curated input and its applier, on
the pattern of the other curated inputs, so a rebuild reproduces it. The corpus carries the pin as a
new `Sense.is_best` field (`00_start.md` Q1, a), which goes in lang-tutor's planned release. Context: [`00_start.md`](00_start.md).

## Plan

- `data/curated/best_senses.jsonl`: lemma id, concept id, reviewer fields (model, prompt hash,
  batch); latest row per lemma wins.
- Add `is_best: bool = False` to `Sense`, its Parquet column, and the frozen-API doc.
- The applier sets the pin at build and records applied and stale counts in `_build.json`, like
  the look-alike input.
- The drill table orders a pinned sense first.
- Tests, and the rebuild guide and `docs/library/` updated.

## Done when

- A pinned row changes the card's best sense after a rebuild, and a stale row is counted, not
  fatal.
- `make check` passes.
