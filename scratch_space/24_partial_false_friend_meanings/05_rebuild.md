---
status: planned
---

# Phase 5 - Rebuild and release

## Overview

Rebuild the corpus with the labels, measure the flag against acerta's read, and release.
Context: [`00_start.md`](00_start.md) (Q6); depends on [`04_full_run.md`](04_full_run.md).

## Plan

- Rebuild per `docs/guides/rebuild_corpus.md`; the quality gate passes; the seed restored.
- Measure: flagged pairs per language; against acerta's 274 read partial decoys, how many of the
  104 shared are flagged and how many of the 170 good are; the `w` pairs; the full pairs
  labelled `s`, listed as candidates for a look-alike re-check.
- 0.12.0: the version, the changelog, the frozen API line (Q6).
  The tag `v0.12.0` goes on the merge commit on `main`, as `v0.11.0` did, when the user asks for
  the merge; the merge stays their decision.

## Done when

- `make check` passes on the rebuilt corpus; the measurement logged in `tracking.md`.
- The folder closed: `00_start.md` at `done`, priority 0.
