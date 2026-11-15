---
status: done
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

## What the implementation found

- The stand-in did not need a change in `enrich`: the build already passes a
  `{(text, language): zipf}` table, where a missing key means no frequency, so
  `with_bucket_zipf` adds the bucket's value for the bucketed words the table lacks, and
  `enrich` scores and splits it like any count (the sense stays flagged estimated, as every
  pt sense is). A word wordfreq does know keeps its count.
- `_build.json` gains `commonness_buckets: {applied, stale}`; a pipeline test asserts it.
- Expected on the next rebuild, not measured until then: 4,045 words get a stand-in;
  the 1,261 common and uncommon ones reach 2.5 or more and pass acerta's floor of 2.0,
  the 2,784 rare ones stay under it; 769 dropped words leave the corpus.
