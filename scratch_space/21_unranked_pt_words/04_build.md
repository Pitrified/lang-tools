---
status: planned
---

# Phase 4 - Buckets in the build

## Overview

The drops already apply through `apply_form_drops`. The buckets need a stage.

## Plan

- A loader for `commonness_buckets.jsonl` and, in `enrich`, a stand-in zipf for a sense
  whose lemma has no token frequency and a bucket: common 3.5, uncommon 2.5, rare 1.5,
  chosen so the card floor of 2.0 keeps common and uncommon and leaves rare out. The
  stand-in feeds the CEFR score and the sense frequency, and the sense stays flagged
  estimated.
- `_build.json` counts the buckets applied and the stale rows.
- Tests on synthetic tables; docs in `docs/library/lexicon.md` (frequency and CEFR) and the
  curated files table.

## Done when

- `make check` passes.
