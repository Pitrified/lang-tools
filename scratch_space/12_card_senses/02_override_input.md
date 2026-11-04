---
status: done
---

# Phase 2 - override input

## Overview

A reviewed best sense has to reach the drill table. Add the curated input and its applier, on
the pattern of the other curated inputs, so a rebuild reproduces it. The corpus carries the pin as a
new `Sense.is_best` field (`00_start.md` Q1, a), which goes in lang-tutor's planned release. Context: [`00_start.md`](00_start.md).

## Plan

- `data/curated/best_senses.jsonl`: lemma id, concept key (the slug-independent half of the
  concept id, as the form drops use), reviewer fields (model, prompt hash, batch); latest row
  per lemma wins, and a row with no concept retracts a pin.
- Add `is_best: bool = False` to `Sense`, its Parquet column, and the frozen-API doc.
- The applier sets the pin at build and records applied and stale counts in `_build.json`, like
  the look-alike input.
- The drill table orders a pinned sense first.
- Tests, and the rebuild guide and `docs/library/` updated.

## Done when

- A pinned row changes the card's best sense after a rebuild, and a stale row is counted, not
  fatal.
- `make check` passes.

## What the implementation found

- **Shape:** `ingestion/best_senses.py` holds `BestSense`, `load_best_senses` (latest row per
  lemma, accepted only) and `apply_best_senses`, which sets `Sense.is_best` after every drop in
  `build_initial` and reports `best_senses: {applied, stale}` in `_build.json` and on
  `BuildSummary`. The row keys on `concept_key`, not the full concept id, so a re-slug does not
  make it stale.
- **The pin is ordered first** in both the drill table's best-sense pick and
  `lemma_sense_cards`, as `coalesce(s.is_best, 0) DESC`, so a corpus written before the column
  existed reads as unpinned.
- **Cache:** the store cache is keyed on the Parquet signature plus `CACHE_VERSION`, so a warm
  `_store.sqlite` from before would have no `is_best` column; the version went from 8 to 9.
- **Backward reads:** the lean Parquet path reads a missing column as `None`, and the model
  path takes the default, so an older corpus still loads.
- **The seed will change.** The next transform run exports `"is_best": false` on every row of
  the committed `data/bootstrap/senses.jsonl`; that diff is the schema change, not drift. The
  corpus has not been rebuilt in this phase: there are no pins yet, so the next rebuild is
  phase 4's.
- Tests: `tests/lexicon/ingestion/test_best_senses.py` (latest row wins, retraction, proposed
  rows ignored, applied and stale counts), `test_reviewed_best_sense_pins_the_card` (a pin
  changes the card through a rebuild), `test_pinned_sense_beats_frequency` (store order).
  `make check` green (412 passed), `make docs-build` clean. Docs: `Sense`, `docs/library/lexicon.md`
  (the model, the pick, the curated-inputs table), `frozen_api.md`, `rebuild_corpus.md`.
