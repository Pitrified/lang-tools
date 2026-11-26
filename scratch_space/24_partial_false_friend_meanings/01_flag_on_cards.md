---
status: planned
---

# Phase 1 - The flag on the cards

## Overview

The data path first, as folder 23 did with `means`: a curated row sets a flag on the edge and the
card's look-alike carries it, so the review in phases 3 and 4 only fills a file the build
already reads.
Context: [`00_start.md`](00_start.md) (Q1, Q2, Q3).

## Goals

1. A curated log row per reviewed pair (`shared_meaning_log.jsonl`, latest row per pair wins)
   with the label (`s`, `d` or `w`), the edge case mark, the reason, the batch,
   the model and the rulebook hash.
2. The build applies it: `LookalikeRelation.shares_main_meaning` (default false), a `lookalikes`
   column, `CACHE_VERSION` 12; only `s` sets it; a row for a pair with no false-friend edge
   (a cognate, or no edge) is stale and skipped, as `apply_lookalikes` does.
3. `LookalikeHint.shares_meaning: bool = False`, filled by `_card_lookalikes`.

## Plan

- The row model and its loader next to the other curated appliers in `lexicon/ingestion/`,
  applied in `build_initial` after the look-alikes.
- The column through the Parquet codec and the SQLite cache, as `kind` went in (v8).
- Docs: `docs/library/lexicon.md`, `docs/library/frozen_api.md` (the field, additive),
  `docs/guides/rebuild_corpus.md` if it lists the curated files.

## Tests

- A fixture with a pt word, a partial it look-alike and a full en one: an `s` row flags its pair
  only, partial or full; a later `d` or `w` row for the same pair clears it; a row for a cognate
  or an unknown pair is skipped; a card's hint carries the flag; a cognate hint never does.

## Out of scope

- The review and its harness (phase 2).
- Anything acerta does with the flag.

## Done when

- `make check` passes; `make docs-build` is clean.
- An empty log builds the same corpus as today, every flag false.
