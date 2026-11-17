---
status: in progress
---

# Phase 5 - Rebuild and release

## Overview

Rebuild with the reviewed rows, measure, release, and hand acerta a new asset.
Context: [`00_start.md`](00_start.md), depends on [`04_full_run.md`](04_full_run.md).

## Goals

1. A rebuild; the checks C1, C2, C3, C6, C7 and C8 re-run, with before and after counts.
2. The quality gate passes, including "definition == lemma".
3. Release 0.10.0 with its changelog (the `[Unreleased]` section and the "unreleased" note
   on `Sense.is_lead` in `docs/library/frozen_api.md` get the version); acerta's card and meanings assets re-exported on an
   acerta branch, its export ordering a meaning's words by `Sense.is_lead` first.

## Done when

- The counts are logged, `make check` passes, the tag is local for the user to push.

## What the implementation found

- Rebuilt on this branch: lemmas 341,353 to 341,144, senses 577,087 to 576,733, look-alikes
  6,763 to 6,748; 84 leads set, 11 gloss overrides applied, none stale. Drill cards 19,599 to
  19,414 (the dropped pre-1990 and misspelled words).
- Checks after: plural pairs in one meaning 614 to 508 (407 to 312 cards), feminine pairs 349
  to 316 (201 to 173 cards); lead meanings still led by an -ing verb form 207 to 130 (the ones
  the review kept). C6 to C8 were read inside the review, not re-run as rules.
- Spot checks: *carreira* leads with "career", *existência* "existence", *organismo*
  "organism", *entrega* "delivery"; *resinas* a form of *resina*; *pre-escolar* and *actriz*
  gone. *canal* still lists *canais* and *cachimbo*: its meaning is not among the 1,705
  reviewed.
- The quality gate passes in full: the "definition == lemma" row (*jogar dados*) is gone. The
  seed did not move. `make check` 600 passed.
- Version 0.10.0 with its changelog; no tag (the user's, with the push). The read API on 8010
  restarted on the new corpus. acerta's re-export is the next step.
