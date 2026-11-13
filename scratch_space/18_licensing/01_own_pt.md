---
status: draft
---

# Phase 1 - pt from own-pt

## Overview

Build the pt backbone from upstream own-pt 1.0.0 (CC BY 4.0) instead of omw-pt 1.4 (CC BY-SA),
so no share-alike row is left when phase 2 writes the CC BY 4.0 notice.
Context: [`00_start.md`](00_start.md) Q1 and the own-pt probe.

## Goals

1. The build reads pt from `own-pt:1.0.0` through `wn`, taking its words and word-to-concept
   links, not its definitions or examples (some are Wikipedia text, CC BY-SA).
2. The cards for frequent pt words are as good as before, or the differences are known and
   accepted.
3. The curated rows that lose their pair are re-pointed or retired by new reviewed rows, never
   by hand edits to the corpus.

## Plan

- Map pt to `own-pt` in `sources/omw.py` (`OMW_LEXICONS` and the version per lexicon, since
  own-pt is `1.0.0`, not `1.4`); `acquire.download_omw` fetches it.
- Drop own-pt's definitions and examples at the adapter, with a test.
- Check whether the spelling reform (`respell_pt`) still applies: own-pt may spell differently.
- Rebuild into a separate data folder first and compare with the current build on 500+ frequent
  pt words: card present, best sense, gloss, look-alikes. Deep probe: writes a second
  `lexicon/`, about the 140 s and 1.5 GB of the July rebuild; to be approved before it runs.
- Fix what the comparison finds through curated rows: the 8 best-sense pins and 191 look-alike
  words that lose their pair, the 53 sense additions that become moot; check the lost frequent
  words (*Brasil*, *sobre*, *há*, *qual*, *deve*, *enquanto*).
- Rebuild in place, regenerate the bootstrap seed, update `docs/library/lexicon.md` and
  `docs/guides/rebuild_corpus.md` where they name omw-pt.

## Out of scope

- fr, which stays out of the shipped dataset (Q2, Q8).
- The license files and card (phase 2).
- own-pt v1.1.0, which is not in the `wn` index.

## Done when

- The build's pt rows all come from own-pt, `_build.json` names it, and no own-pt definition or
  example is in the corpus.
- The 500+ word comparison is recorded here, with every regression fixed or accepted.
- `make check` and `make docs-build` pass.
