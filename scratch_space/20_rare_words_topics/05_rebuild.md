---
status: done
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

## What the implementation found

- The build ran as the transform notebook runs it, from this branch: the 2026-11-13 corpus
  predates every `feat/19_pt_glosses` commit, so no curated row was lost. Counts are
  identical (342,122 lemmas, 117,725 concepts, 577,901 senses).
- Bands: A1 8,349, A2 15,081, B1 32,208 unchanged; B2 30,001 to 88,532, C1 34,140 to
  183,949, C2 458,122 to 249,782.
- Topics: 82,764 concepts tagged (was 80,856), 2,744 `medical`; no hypernym root stale.
- The seed moved as intended (`data/bootstrap/senses.jsonl`, the bands); `make check`
  passes on it, 571 tests.
- The quality gate fails one invariant, "definition == lemma": concept
  `c__dice__5277ff536fc6`, pt gloss "jogar dados" (an `llm` gloss) on the sole pt member
  "jogar dados". The committed report was last refreshed on 2026-11-11, before pt moved to
  OpenWordnet-PT, and nothing here touches definitions; parked in
  `scratch_space/open_points.md`, "pt gloss equal to its word". The report is committed as
  it reads.
- Version 0.8.0 with a changelog entry; the tag is left for the merge to `main`, which is
  the user's.
- The read API on port 8010 was restarted on the new corpus. Through the store: doença B1
  medical, febre B2 medical, hemorragia C1 medical, insulina C1 body, cortisona C2
  materials (a hormone in WordNet, so medical off keeps it, as the user wanted),
  atelectasia C2 medical and below the floor, voluto B2 with no frequency and below the
  floor.
- acerta's export re-run moves to acerta (`plans/01_bootstrap/09_topic_picker.md`), since
  the asset gains topics and the app has to read them.
