---
status: draft
---

# Phase 2 - license files and dataset card

## Overview

Write the licenses down: MIT for the code, CC BY 4.0 for the dataset, with every upstream
source credited. Runs after phase 1, so no share-alike pt row is under the CC BY notice.
Context: [`00_start.md`](00_start.md) Q3 to Q9, depends on [`01_own_pt.md`](01_own_pt.md).

## Goals

1. Anyone opening the repo finds the code license and the data license at the root.
2. Anyone bundling the dataset in an app, fala included, can copy the attribution text from one
   file.
3. The license records in the code match the verified licenses.

## Plan

- `LICENSE`: MIT, for lang-tools; `license = "MIT"` in `pyproject.toml`. lang-tutor gets the
  same, in its own repo and commit.
- `DATA_LICENSE.md`: CC BY 4.0 for the dataset, with
  - each upstream source, its license and the attribution it asks for: Princeton WordNet 3.0,
    own-pt, MCR Spanish, MultiWordNet, CILI, wordfreq and its sources (SUBTLEX, OpenSubtitles);
  - the statement that the upstream wordnets stay available under their own terms;
  - a line that the fr rows of the test seed are WOLF, under CeCILL-C.
- `docs/library/dataset_card.md`: sources, licenses, coverage per language and the estimated
  share of frequency and CEFR values from `_build.json`; added to the docs nav.
- `staging/base.py` `KNOWN_LICENSES`: wordfreq data is CC BY-SA 4.0.
- Remove the plan citations from the `sources/__init__.py` and `staging/__init__.py` docstrings;
  where they lean on a licensing decision, point at the card.
- `docs/library/lexicon.md` and `docs/guides/rebuild_corpus.md`: a pointer to the card where they
  mention the license manifest.

## Out of scope

- What is shipped and how (`17_distribution`); the license files say what applies to it.
- fala's own licenses screen, which copies from `DATA_LICENSE.md`.

## Done when

- `LICENSE`, `DATA_LICENSE.md` and the card exist and agree with `00_start.md`.
- No plan citation is left in `src/`; `plans.py check --citations` passes.
- `make check` and `make docs-build` pass.
