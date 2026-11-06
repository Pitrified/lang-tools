---
status: planned
---

# Phase 1 - tooling

## Overview

Everything the review needs before an agent runs: the curated input of sense additions and its
build stage, the extended review harness, and the rules. Context: [`00_start.md`](00_start.md),
"The mechanism", Q1 to Q8.

## Goals

1. `data/curated/sense_additions.jsonl`: a `SenseAddition` row (word, language, `lemma_id`,
   `concept_key`, `add`, `form_note`, reason, status, model, prompt_sha, batch), latest row wins
   per (lemma, concept), loaded next to `load_form_drops` and `load_best_senses`.
2. A build stage in `build_initial` right after the drops: adds the sense, creates the lemma when
   the build lacks it, counts stale rows (concept gone), reports in the manifest.
3. `Sense.form_note` and `LemmaCard.form_note`, optional (Q7 a).
4. The harness: label action `a<concept key>` with an optional form note (adds the link, pins
   it); removed lemmas served as worklist items with no card (their dropped links shown); hidden
   gold covering the new action.
5. `sense_review_cli concepts --word <en word>` (key, gloss, members) and `add` (hand
   correction, through `_correct()` like `pin`).
6. A second-review mode (Q8): serve chosen items again under another batch id, blind to the
   first labels, and an `agreement` report over the two (per action, and on the changes).
7. Rules: the new action, verb forms (Q1), capitalisation (Q2), wrong members (Q4), and a free
   reason for any other wrong card, in
   `docs/guides/sense_review.md` (its hash changes, deliberately); the how-to guide
   `docs/guides/missing_senses.md` for running the pass on another language (Q5); the
   sense-review skill; `docs/library/lexicon.md`; `docs/library/frozen_api.md` for Q7.

## Plan

- Review this plan against the code first: where provenance tags go (`lemma_sources`,
  `sense_sources`) and which tag an addition gets; whether every gate invariant holds for a
  sense with no OMW source; how `apply_batch` writes the pin for an added sense, whose sense id
  only exists after the build.
- Refuse an addition on a closed-class word with a named error (it would re-add what the rule
  just dropped).
- Tests: the stage (new lemma, existing lemma, retraction, stale), the new label action and its
  validation (unknown concept key), removed-lemma items, the second review and agreement, both
  commands.

## Out of scope

- Running any review batch (phase 2). New concepts: every target must already exist.

## Done when

- `make check` green; a build on the bootstrap seed with one addition row shows the lemma, the
  sense and the form note on its card; docs build strict.

## What the implementation found
