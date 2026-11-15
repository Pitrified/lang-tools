---
status: draft
---

# Phase 4 - Re-cut the bands

## Overview

Applies the option the user picks after [`01_band_analysis.md`](01_band_analysis.md).
Written in full once that choice is made.
Context: [`00_start.md`](00_start.md).

## Plan

- The chosen cutoffs or quotas in `ingestion.enrich`, `cefr_validation` re-run, the
  numbers in `docs/library/lexicon.md` (CEFR) and `docs/library/dataset_card.md`.
- Tests that pin band edges updated to the new values.

## Done when

- `make check` passes; Kelly agreement reported next to today's.
