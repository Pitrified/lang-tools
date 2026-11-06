---
status: done
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

Plan review against the code (2026-11-06), folded in:

- `serve_batch` skips every lemma with a `BestSense` row, and all 1,060 items have one. The
  review needs a `recheck` mode, as for the look-alikes: serve chosen lemma ids whose latest
  `BestSense` row was not written under the current rulebook.
- The second review (Q8) must not write curated rows, or it would override the first: a shadow
  apply validates the labels and keeps the outcome per lemma (card concept, drops, additions)
  under the work folder; `agreement` compares two batches' outcomes.
- Removed lemmas are not in the store: their item is built from their drop rows (the dropped
  concept keys with the concepts' glosses). `k` keeps them removed, `a` brings them back.
- Pins key on (lemma id, concept key), not on a sense id, so pinning an added sense needs nothing
  new.
- Provenance: added lemmas and senses take `SOURCE_MANUAL` (`ingestion.transform`). The stage
  runs before `enrich`, so frequency, CEFR and their flags are filled as for any sense and the
  frequency and CEFR invariants hold.
- A new lemma's part of speech comes from its concept's lexfile (`noun.quantity` -> noun).
- `form_note` follows the path `is_best` took: `Sense`, the codec schema, `CACHE_VERSION` 10,
  the `lemma_drill` table and both card queries, `LemmaCard`.
- Refuse an addition on a closed-class word with a named error (it would re-add what the rule
  just dropped).
- Tests: the stage (new lemma, existing lemma, retraction, stale, closed-class refusal), the new
  label action and its validation, removed-lemma items, recheck, shadow apply and agreement,
  both commands, `form_note` on the card.

## Out of scope

- Running any review batch (phase 2). New concepts: every target must already exist.

## Done when

- `make check` green; a build on the bootstrap seed with one addition row shows the lemma, the
  sense and the form note on its card; docs build strict.

## What the implementation found

- Built as planned: `ingestion.sense_additions` (row, loader, stage right after the drops),
  `Sense.form_note` to `LemmaCard.form_note` (cache v10), `LexiconStore.get_concept_by_key`,
  and in `sense_review` the `aKEY` action with a `{form note}`, removed-lemma items,
  `recheck_batch` (with `shadow`), `agreement`, `add_sense`, `find_concepts`. Rulebook, skill,
  `docs/guides/missing_senses.md`, `lexicon.md`, `frozen_api.md`, `rebuild_corpus.md` updated.
  `make check` green (433), docs build strict.
- Added beyond the plan: a `drop` hand correction. The rulebook has the reviewer write fixes that
  are not about the item in hand (a wrong member of a looked-up concept, a capitalised name to
  link) to a notes file, which the orchestrating session checks and applies with `drop` and
  `add`; without `drop` there was no way to apply the first kind.
- Not done: hidden gold for the new action (goal 4). The gold set has no item whose right card
  is a concept the lemma lacks, and the clear candidates (*sim*, *vinte*, *seis*) are worklist
  items; a gold lemma leaves the worklist. Moved to phase 2 as a step.
- On the real corpus `removed_lemmas` finds 64 pt lemmas: the 60 the review removed and 4 gold
  lemmas dropped the same way. The rulebook change makes all 1,064 servable by `recheck`.
