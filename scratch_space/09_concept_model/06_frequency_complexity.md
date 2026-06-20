---
status: draft
---

# Phase 6 - frequency & complexity

> Draft. Scope sketch to hold the overarching story; not yet the plan of record.

> **Frequency is a priority signal, not a hard cap (decided 2026-06-18).** The target is
> support for a language-learning app, but we do **not** hard-filter by frequency: a
> low-frequency lemma is kept when it is well-connected in the graph or pedagogically
> important (e.g. irregular verbs), which a top-N cut would wrongly drop. So frequency
> here orders **enrichment priority** and surfaces a learner-facing core; it does not
> delete rows. Blanket long-tail pruning is only an **optional cleanup pass** for a
> specific junk pattern (multiword/`PSEUDOGAP`-style noise), not a corpus boundary. This
> keeps the phase as annotation + prioritization. Context:
> [`05.4_data_quality.md`](05.4_data_quality.md), "emerging direction" (2).

> **From the 5.5 cleanup (2026-06-20).** The kaikki-free rebuild carries the inputs this
> phase needs straight from OMW: `sense.id` plus `sense.counts()` / `tag_count` (SemCor,
> English) as the weights for splitting token frequency across senses, and `synset.lexfile`
> as a coarse difficulty class. Example sentences land on the `Sense` edge alongside these
> signals (attached at each source's granularity; see
> [`05.5_cleanup.md`](05.5_cleanup.md) Step 4). Frequency and graph connectivity also rank
> which concepts the phase-8 enrichment touches first.

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
