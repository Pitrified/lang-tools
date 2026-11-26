---
status: done
---

# Phase 1 - The flag on the cards

## Overview

The data path first, as folder 23 did with `means`: a curated row sets a flag on the edge and the
card's look-alike carries it, so the review in phases 3 and 4 only fills a file the build
already reads.
Context: [`00_start.md`](00_start.md) (Q1, Q2, Q3).

## Current state

- `LookalikeRelation` (`lexicon/relations.py`): `lemma_id_a < lemma_id_b`, `kind`,
  `similarity_score`, `explanation_notes`; stored through `lexicon/codec.py` (`_COLUMNS` and the
  pyarrow schema of `lookalikes`); the SQLite cache follows the codec columns.
  A column a corpus predates reads as null and the field takes its default (`model_from_row`),
  so the committed seed and an old corpus load without a rebuild.
- The build (`ingestion/pipeline.py`) applies `lookalikes.jsonl` with `apply_lookalikes`, after
  `drop_rare_traps`; then the best-sense pins and the lead translations, each counted in the
  manifest (`{"applied": .., "stale": ..}`) and on `BuildSummary`.
- `ingestion/lead_translations.py` is the template: a row model, `load_*` (latest row per key),
  `apply_*` returning `(applied, stale)`, logged; commit `746aa2d` added it end to end
  (codec, store, pipeline, tests, docs).
- `_card_lookalikes` (`lemma_store.py`) fills `LookalikeHint`; `CACHE_VERSION` is 11.
- `false_friend_meaning_log.jsonl`'s `MeaningLogRow` is the shape of a review log row:
  `batch`, the word, `label`, `edge_case`, `reason`, `rulebook_sha`.

## Plan

1. `lexicon/ingestion/shared_meanings.py`, narrative module docstring:
   - `SHARED_MEANING_LOG_FILE = "shared_meaning_log.jsonl"`;
   - `SharedMeaningRow`: `batch`, `target_id` / `target_text` (the pt word), `known_id` /
     `known_text` / `known_language` (the look-alike), `kind` (the edge's kind when reviewed, a
     review aid), `label: Literal["s", "d", "w"]`, `edge_case`, `reason`, `model`,
     `rulebook_sha`; a `pair` property, the two ids sorted, as the edge stores them;
   - `load_shared_meanings(data_fol)`: the latest row per pair, empty when the file is absent;
   - `apply_shared_meanings(edges, rows) -> (flagged, stale)`: sets
     `LookalikeRelation.shares_main_meaning` on the edge of each `s` row; a `d` or `w` row sets
     nothing (the latest row already won); a row whose pair has no edge, or a cognate edge, is
     stale and skipped; logs both counts.
2. `LookalikeRelation.shares_main_meaning: bool = False`, documented; the codec column
   (`pa.bool_()`), after `explanation_notes`.
3. The build: `apply_shared_meanings` right after `apply_lookalikes`; manifest
   `"shared_meanings": {"flagged": .., "stale": ..}`; `BuildSummary.shared_meanings_flagged` /
   `shared_meanings_stale`.
4. The store: `CACHE_VERSION = 12` with its comment line; `_card_lookalikes` selects the column;
   `LookalikeHint.shares_meaning: bool = False`, documented, true only for a false friend whose
   edge is flagged.
5. Docs: `docs/library/lexicon.md` (the curated-file table row, a paragraph next to the lead
   translations one, the manifest key), `docs/library/frozen_api.md` (a "since v0.12.0" clause
   after `means`). The changelog waits for phase 5.

## Tests

- `tests/lexicon/ingestion/test_shared_meanings.py`: the latest row per pair wins (an `s` then a
  `d` leaves the edge unflagged, a `d` then an `s` flags it); `s` flags a partial and a full
  edge, and only its own pair; a row for a cognate edge and a row for a pair with no edge count
  as stale; no file loads as empty.
- `tests/lexicon/test_lemma_cards.py`: on the `_means_store` fixture, a flagged edge gives
  `shares_meaning` true on that hint only; the other hints and a cognate stay false.
- `tests/lexicon/test_codec.py`: a lookalikes row with no `shares_main_meaning` loads as false.
- `tests/lexicon/ingestion/test_pipeline.py`: a build with a log row flags the edge on disk and
  reports it in the manifest, as the lead-translation test does.

## Out of scope

- The review and its harness (phase 2).
- Anything acerta does with the flag.

## Done when

- `make check` passes; `make docs-build` is clean.
- A fixture build with no log file has every flag false; the real rebuild is phase 5.

## What the implementation found

- Built by a Sonnet subagent at medium effort from this file; it wrote the labels' meaning from
  their letters alone (`s` as the pt word's *main* meaning, `w` as "undecided") into the
  docstrings and `lexicon.md`, with an invented example. Corrected by hand: `s` means the pt word
  is also used for the look-alike's main meaning, `w` that the main meaning shown is wrong.
  Phase 2's prompt defines each label in one line.
- A cognate guard in `_card_lookalikes` was dropped: the build never flags a cognate edge
  (`apply_shared_meanings` counts such a row as stale). `SharedMeaningRow.kind` is required.
- A `d` or `w` row on a live edge counts as neither flagged nor stale.
