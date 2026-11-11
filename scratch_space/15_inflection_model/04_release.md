---
status: in progress
---

# Phase 4 - release v0.7.0

## Overview

Release the model and bump lang-tutor's pin, as `16_card_pos_filter/03_release.md` did.
Context: [`00_start.md`](00_start.md); depends on phases 1 to 3.

## Plan

- CHANGELOG `## [0.7.0]`: the form table and its source and licence, the build stage and its
  counts, the card filter and its default.
- `pyproject.toml` 0.7.0, `uv lock --offline`, lock revision back to 3.
- Release commit, `--no-ff` merge into main from a message file, annotated tag `v0.7.0` on the
  merge, branch moved onto the merge before the closure commit. The user pushes.
- lang-tutor: branch `deps/lang-tools-v0.7.0`, pin and lock, `make undev`, `make check`, merge
  into its main, restart 8000, run its four drill queries against 8010.

## Done when

- The tag is pushed by the user, lang-tutor passes `make check` on v0.7.0, and its drills draw no
  form card.
