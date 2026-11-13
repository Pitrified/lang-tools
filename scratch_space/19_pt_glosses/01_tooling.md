---
status: planned
---

# Phase 1 - Tooling

## Overview

The batch job the subagents run, on the plumbing the two reviews share.
Context: [`00_start.md`](00_start.md).

## Goals

1. A subagent can serve a batch of 200 missing pt glosses, write them, and apply them, with every
   gloss screened before anything is written.
2. The existing 174,348 curated rows cannot be lost by this job or by the notebook.
3. The 9 concepts between the card's 8,868 and today's 8,877 are explained.

## Plan

- `src/lang_tools/lexicon/ingestion/gloss_write.py`:
  - constants: `BATCH_SIZE = 200`, `WORK_SUBDIR = "work/gloss_write"`,
    `LOG_FILE = "gloss_write_log.jsonl"`, `RULES` = the v3 prompt path.
  - `serve_batch(data_fol, batch, size)`: under `review_batches.locked`, re-prints a reserved
    batch, else takes `missing_glosses(data_fol, ["pt"])` minus the keys in a pending batch file
    or in the batch log, first `size` by key (the key is a hash, so the order is effectively
    random), and writes `data/work/gloss_write/<batch>.jsonl`.
    Not "minus every key with a curated row": the October run left one pt row rejected, and that
    concept still needs its gloss. Written rows reach the corpus only at the rebuild, so the log
    is what stops a key being served twice.
  - `render_batch(items)`: `n | English gloss | en words | pt words`.
  - `apply_batch(data_fol, batch, text, rules_path)`: parses `n<TAB>gloss` lines; collects every
    problem (unknown, missing or doubled number, and each `check_glosses` reason) and raises
    `review_batches.LabelError`; on success, under the lock, `append_rows` the `GlossProposal`
    rows (`status="proposed"`) to the curated file and one `GlossWriteLogRow` (batch, rules
    hash, writer, date, count, keys) to the log, and removes the pending file.
  - `write_status(data_fol)`: worklist left, batches applied, pending, glosses written.
- `gloss_write_cli.py` with `serve`, `apply`, `status`, the shape of `lookalike_review_cli`
  (`NOT APPLIED, fix and re-run:` on a `LabelError`);
  and `correct --key pt:<concept_key> --gloss <text>`, which appends an accepted
  `GlossProposal` to `gloss_overrides.jsonl` (the build applies overrides before the backfill,
  and they win), for the wrong glosses the pilot and the sampled review find.
- `.claude/skills/gloss-write/SKILL.md`: read the rules once, serve, write the labels file under
  `data/work/gloss_write/`, apply until it passes, report in four lines; orchestration notes.
- The notebook's check cell: read the existing curated rows and write them back with the new
  ones appended, instead of writing the new ones alone.
- Q5: diff the pt worklist keys against the 2026-11-13 build's gloss coverage to name the 9.
- Tests in `tests/lexicon/ingestion/test_gloss_write.py` on the seed: serve excludes pending and
  written keys, re-serve is idempotent, apply refuses each problem kind and writes nothing,
  apply appends without touching existing rows.
- Docs: `docs/library/lexicon.md` (or the page that describes the backfill) gains the agent path;
  `docs/guides/` gets nothing new, since the rules stay in the prompt (Q2).

## Out of scope

- Any batch beyond a smoke test (phase 2).
- fr and it leftovers the worklist also returns.

## Done when

- `make check` passes.
- A smoke batch of 5 items served, written by hand and applied on a copy of the curated file
  behaves as planned, then is removed (no row from it stays in `data/curated/`).

## What the implementation found
