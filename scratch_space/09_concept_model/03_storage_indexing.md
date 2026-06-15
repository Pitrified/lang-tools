---
status: draft
---

# Phase 3 - storage & indexing analysis

> Draft. Scope sketch to hold the overarching story; not yet the plan of record.

## Overview

A research/decision phase (mostly analysis, little code) that picks the on-disk
format for the lexical dataset and validates it stays git-LFS friendly at scale.
It gates the store layer (phase 4) and ingestion outputs (phase 5), and may feed
back into the models (phase 2). Context:
[`00-concepts-brainstorm.md`](00-concepts-brainstorm.md), "Storage format,
git-LFS friendliness, and scaling".

## What this phase will cover

- **Format trade-off study** - line-oriented CSV/JSONL (diffs and appends
  cleanly, LFS-friendly, human-inspectable) vs a single SQLite file (queryable,
  compact, but an opaque binary blob that LFS re-uploads wholesale on each
  change). Concrete question: can a built SQLite artifact live usefully in LFS, or
  is it only worth it once read patterns demand indexed queries?
- **Scale estimate** - OMW across five languages is ~10^5 synsets and ~10^6
  senses. Measure real on-disk size per format (concepts, lemmas, senses, edge
  tables) and the import-time cost of loading everything into memory (today's
  model) vs lazy/indexed access.
- **git-LFS mechanics** - which paths to track via LFS, partitioning strategy
  (per-language? per-table?) so a single edit does not re-push the whole corpus,
  and the effect on clone size and CI.
- **Performance and limits** - import latency, memory footprint, and the
  threshold where the in-memory `_LEMMAS_BY_ID` dict approach stops scaling and a
  real index (SQLite FTS, on-disk KV) is warranted.

## Deliverable

A short decision memo (folded back into the brainstorm) confirming or overturning
the provisional lean: **partitioned JSONL/CSV under LFS now, SQLite build
artifact only if query latency or memory become real problems.**

## Out of scope

- Implementing the loaders/indexes (phase 4) and producing the data (phase 5).

## Done when (draft)

- Format decided with measured numbers backing it; `.gitattributes` LFS strategy
  drafted; the memo is recorded in the brainstorm and tracking Log.
