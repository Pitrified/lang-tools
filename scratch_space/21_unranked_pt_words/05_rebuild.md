---
status: done
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

## What the implementation found

- Rebuilt on `main` plus this branch (0.8.0 underneath, merged locally as `780788a`).
  Lemmas 342,122 to 341,353 (769 fewer, exactly the dropped words), senses 577,901 to
  577,087; 4,045 bucket stand-ins applied, none stale; the review's 813 drop rows remove
  813 senses (1,076 dropped in all with the earlier ones).
- pt: 63,692 to 62,923 lemmas; pt words with no frequency 8,597 to 3,783, every one of
  them multiword (out of scope).
- Bands: A1 8,349 (same), A2 15,080, B1 32,191, B2 87,992, C1 179,759 (from 183,949), C2
  253,716 (from 249,782): the rare words that sat in C1 on the mid-scale default moved up.
- Spot checks through the store: voluto, magestoso, walkout, canodachaminé gone; peúga C1
  at 3.5, túlipa C1, conquiliologia, coccinela and favelar C2 at 1.5.
- The seed did not move; `make check` passes, 584; the quality gate reads as before, with
  the one known "definition == lemma" row.
- Version 0.9.0 with a changelog; no tag (the user's, with the push). The read API on 8010
  restarted; acerta re-exported (acerta-word-drills, `plans/01_bootstrap/tracking.md`).
