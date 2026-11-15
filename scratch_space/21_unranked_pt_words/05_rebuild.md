---
status: planned
---

# Phase 5 - Rebuild and release

## Overview

The rebuild must carry 0.8.0 (`20_rare_words_topics`), so it runs once that branch is on
`main` and this one is rebased or merged onto it.

## Plan

- Agree the rebuild with the user (about 4.5 minutes, the read API restarted).
- Before and after: pt lemmas, the bands, the words with no frequency left.
- Seed, quality report, dataset card, a version and changelog; acerta re-exported.

## Done when

- `make check` passes; the user has the numbers.
