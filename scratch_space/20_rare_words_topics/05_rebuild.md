---
status: planned
---

# Phase 5 - Rebuild and release

## Overview

Phases 2 and 4 change what the build writes; one rebuild carries both.
Context: [`00_start.md`](00_start.md).

## Plan

- Agree the rebuild with the user first: about 4 min for `build_initial` and 30 s for the
  first store load (`docs/guides/rebuild_corpus.md`); it replaces `data/lexicon/`, which is
  local and gitignored, and the read API on port 8010 is restarted after it.
- The quality report and `_build.json` checked against the previous build: band sizes,
  `medical` counts per root, stale counts.
- `docs/library/dataset_card.md` counts; the bootstrap seed re-carved and committed if the
  build changes it.
- A version bump and a tag, for lang-tutor and acerta to pin.
- acerta's export re-run with `min_zipf=2.0` and the topics (acerta-word-drills,
  `plans/01_bootstrap/09_topic_picker.md`).

## Done when

- `make check` passes on the new seed; the quality report matches the logged summary.
- The user has the numbers before and after.
