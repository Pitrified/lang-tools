---
status: in progress
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

- `LICENSE`: MIT, for lang-tools, "Copyright (c) 2026 Pietro Maria Nobili" (Q14); `license = "MIT"` and
  `license-files = ["LICENSE", "DATA_LICENSE.md"]` in `pyproject.toml` (hatchling reads both,
  PEP 639); `uv build` shows them in the wheel metadata. lang-tutor gets the same `LICENSE`
  and field, on a lang-tutor branch `feat/license` (Q16).
- `DATA_LICENSE.md`: CC BY 4.0 for the dataset, with
  - each upstream source, its license and the attribution it asks for: Princeton WordNet 3.0,
    own-pt, MCR Spanish, MultiWordNet, CILI, wordfreq and its sources (SUBTLEX, OpenSubtitles);
  - the statement that the upstream wordnets stay available under their own terms;
  - the fr carve-out: the fr wordnet (WOLF) is CeCILL-C and outside the CC BY grant; fr is in
    the local build and in the test seed, and out of the shipped dataset (Q8);
  - the wordfreq line of Q3: the frequency numbers and CEFR bands derive from wordfreq data
    (CC BY-SA 4.0), credited with the sources it names;
  - our own text (glosses, notes, example sentences, inflection form notes) under the same
    CC BY 4.0.
- `docs/library/dataset_card.md`: sources, licenses, coverage per language and the estimated
  share of frequency and CEFR values from `_build.json`; added to the docs nav.
- `staging/base.py` `KNOWN_LICENSES`: wordfreq data is CC BY-SA 4.0.
- Remove the five licensing plan citations ("phase 10") from `sources/__init__.py`,
  `staging/__init__.py`, `staging/base.py` (two) and `llm/runner.py`, pointing at the card
  instead. The other 165 "phase N" mentions in `src/` are Q15.
- `docs/library/lexicon.md` and `docs/guides/rebuild_corpus.md`: a pointer to the card where they
  mention the license manifest.

## Out of scope

- What is shipped and how (`17_distribution`); the license files say what applies to it.
- fala's own licenses screen, which copies from `DATA_LICENSE.md`.

## Done when

- `LICENSE`, `DATA_LICENSE.md` and the card exist and agree with `00_start.md`.
- No licensing plan citation is left in `src/`; `plans.py check --citations` passes.
- `uv build` succeeds and the wheel metadata names the MIT license.
- `make check` and `make docs-build` pass.

## Review (2026-11-13, before execution)

- **Claim corrected:** fr is not only in the test seed but in every local build; the data license
  carves the fr wordnet out of the CC BY grant rather than noting the seed alone.
- **Claim corrected:** the plan named the plan citations of two docstrings; `src/` holds 170
  "phase N" mentions in 44 files, which `plans.py check --citations` does not match. This phase
  takes the five about licensing; the rest is Q15.
- **Added:** the copyright holder (Q14) and where lang-tutor's commit goes (Q16) are the user's.
- **Added:** `license-files` and a `uv build` check, so the license reaches the package metadata
  rather than only the repo root.
