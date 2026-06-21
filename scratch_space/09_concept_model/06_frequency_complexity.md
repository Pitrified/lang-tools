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

> **From the 5.54 exploration (2026-06-21).** The topic notebooks
> ([`notebooks/lexicon_enrich/03_semcor_frequency`, `05_complexity`](../../notebooks/lexicon_enrich/))
> measured the two design questions this phase rested on:
> - **Two distinct frequency signals, and the concept one propagates.** Lemma token
>   frequency is language-level. SemCor concept commonness (counts summed to the ILI) is
>   concept-level: it correlates 0.47 with the independent en frequency list and predicts the
>   *other* language's lemma frequency (es 0.34, it 0.49). So carry a concept-level commonness
>   signal cross-language and refine it per language with that language's token frequency.
> - **The English sense split is the prior for languages with no sense-tagged corpus.** SemCor
>   covers only 17% of en senses (skewed: median 2, max 10,742) and zero non-en senses, but
>   senses share the ILI, so the English `tag_count` distribution is the default weighting for
>   splitting another language's lemma frequency across its senses (`frequency_is_estimated`).
>   Caveat (decision 2026-06-21): the exploration validated *aggregate* concept-commonness
>   propagation, **not** that the within-lemma sense split transfers - that finer check was not
>   run. But there is no other per-sense signal for those languages, so we treat the English
>   split as an **approximate** prior, always flag it `frequency_is_estimated`, and move on
>   rather than block phase 6 on a check we cannot ground without non-en sense-tagged data.
> - **Complexity is mostly concept-level.** Against Kelly CEFR (en, 24,595 concepts) lemma
>   frequency is the strongest signal (pearson -0.66); commonness and hypernym depth add
>   weaker, same-direction signal. The concept-level call travels: 87% of en-easy concepts are
>   also high-frequency in Italian. So compute most of complexity once at the concept level
>   (commonness + depth + lexfile, propagated via ILI) with a thin per-language overlay (token
>   frequency rank, word length). Kelly (en/it, CC-BY-NC-SA) is **validation only, never
>   shipped**; pt/es/fr have no graded list and stay estimated.
>   Caveat (#2): the -0.66 is partly circular - Kelly's CEFR bands were themselves built
>   largely from corpus frequency, so this confirms the pipeline is consistent, not that
>   frequency independently predicts *human-perceived* difficulty. Read it as a sanity check,
>   not independent validation.

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
  `frequency_is_estimated = True`. Since SemCor is English-only but senses share
  the ILI, use the **English sense-tag distribution as the cross-language prior**
  for languages with no sense-tagged corpus (5.54 Topic 3).
- **Concept commonness** (new, concept-level) - sum SemCor counts to the ILI for a
  cross-language commonness signal that propagates (5.54 Topic 3: 0.47 vs en
  frequency, predicts es 0.34 / it 0.49); refine per language with token frequency
  rather than recomputing from scratch.

### Complexity (CEFR)

- Compute most of complexity at the **concept level** (commonness + hypernym depth
  + lexfile, propagated via ILI) with a thin per-language overlay (token frequency
  rank, lemma length/morphology) - 5.54 Topic 5 found the concept-level call holds
  in 87% of en->it cases, and lemma frequency is the strongest single signal
  (pearson -0.66 vs Kelly CEFR en).
- Validate the estimate against a graded list **for en/it only** (Kelly, staged at
  `data/_raw/lexicon/staging/cefr/`); Kelly is CC-BY-NC-SA, **validation-only,
  never merged into the shipped data**.
- Where no graded list exists (pt/es/fr), estimate from the concept-level signal
  plus the per-language overlay and an LLM judgment; set `cefr_is_estimated = True`.
- Cache a coarse lemma-level CEFR (easiest sense) on `Lemma`.

## Open points to resolve here

- The exact sense-frequency approximation per language (the English sense split as
  prior is confirmed usable; the math - smoothing, fallback when a concept has no
  en counts - is still open).
- How much weight the per-language overlay gets on top of the concept-level
  complexity score (Topic 5 says it is thin but non-zero - 13% of en-easy concepts
  disagree in it).
- The CEFR estimation blend and how heavily to trust it (and how to surface
  `*_is_estimated` to the tutor).
- Per-list licensing (hand off specifics to phase 10); Kelly's CC-BY-NC-SA is why
  it stays validation-only.

## Out of scope

- Semantic relations (phase 7); exposing these signals in exercises (lives in
  `lang-tutor`, not this dataset effort).

## Done when (draft)

- Senses carry token/sense frequency and CEFR level (real or flagged-estimated)
  for the five languages; coverage and estimated-share reported.
- `uv run pytest && uv run ruff check . && uv run pyright` passes.
