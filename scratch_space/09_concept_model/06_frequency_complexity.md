---
status: draft
---

# Phase 6 - frequency & complexity

> Draft. Scope sketch to hold the overarching story; not yet the plan of record.

## Overview

Populate the two per-sense learner signals that share one home on the `Sense`
edge: **frequency** ("how common") and **CEFR complexity** ("how advanced"). Both
are subject to the polysemy trap, so both live on the sense, not the bare
`Lemma`. Context: [`00-concepts-brainstorm.md`](00-concepts-brainstorm.md),
"Lemma frequency" and "Lemma complexity (CEFR level)". Builds on the sense edge
from phase 2 and the ingested data from phase 5.

## What this phase will cover

### Frequency

- **Token frequency** (easy, always populated) - from `wordfreq` (MIT), Zipf
  scale, all five languages; cached on `Lemma` as a convenience aggregate (max
  across senses) and copied onto each `Sense`.
- **Sense frequency** (hard) - populate where a sense-tagged source exists;
  otherwise approximate by splitting token frequency across senses using WordNet
  sense-tag counts (`tag_count`, SemCor) as weights, and set
  `frequency_is_estimated = True`.

### Complexity (CEFR)

- Map lemmas/senses to A1..C2 from CEFR-graded word lists (English Vocabulary
  Profile, Oxford 3000-5000, Kelly project for several languages), joined like
  the frequency lists.
- Where no graded list exists, estimate from a blend of frequency band, lemma
  length/morphology, and an LLM judgment; set `cefr_is_estimated = True`.
- Cache a coarse lemma-level CEFR (easiest sense) on `Lemma`.

## Open points to resolve here

- The exact sense-frequency approximation per language.
- The CEFR estimation blend and how heavily to trust it (and how to surface
  `*_is_estimated` to the tutor).
- Per-list licensing (hand off specifics to phase 10).

## Out of scope

- Semantic relations (phase 7); exposing these signals in exercises (lives in
  `lang-tutor`, not this dataset effort).

## Done when (draft)

- Senses carry token/sense frequency and CEFR level (real or flagged-estimated)
  for the five languages; coverage and estimated-share reported.
- `uv run pytest && uv run ruff check . && uv run pyright` passes.
