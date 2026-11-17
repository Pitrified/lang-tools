---
status: planned
---

# Phase 1 - Curated inputs in the build

## Overview

The review needs somewhere to write that the build already reads. Drops have one
(`member_form_drops.jsonl`); a form-of row and a lead translation row do not. This phase adds
both, and the C8 gloss fixes, so a pilot row can be checked end to end by a rebuild.
Context: [`00_start.md`](00_start.md).

## Goals

1. A reviewed form row (pt lemma, concept, base word) that the build turns into a form note on
   that sense, written by `inflections.form_note` from the base's readings, so the sense
   leaves the cards and the meaning's word lists like a rule-made inflection.
2. A reviewed lead row (concept, language, lemma) that puts that word first in a card's
   translations and in `lemmas_for_concept`.
3. Five `gloss_overrides.jsonl` rows for the pt glosses equal to their word (C8).

## Plan

- Form rows: a new curated JSONL with its loader and applier, keyed like the form drops on
  `lemma_id` and `concept_key`, latest row wins, `form: false` retracts. The applier runs after
  the inflection stage. A row whose base does not generate the form by the rules is reported
  and skipped, not guessed.
- Lead rows: decide at the phase review between a field on `Sense` (a frozen-surface
  addition with a default, like `LemmaCard.topics`) and a store-only table filled from the
  curated file. Lean: the `Sense` field, because the corpus Parquet is what the store and the
  read API are built from, and a store-only table would not survive the codec.
- Both appliers counted in the build manifest, like the other curated inputs.
- Tests on the bootstrap seed for each applier, the retraction rows, and the card order.
- The five gloss rows, written by hand from the en glosses, `source` noted.

## Out of scope

- The review harness and any review rows beyond test fixtures (phase 2).
- A rebuild of the full corpus (phase 5).

## Done when

- `make check` passes with the new tests.
- A fixture form row hides *canais* from canal's conduit meaning and its cards; a fixture lead
  row puts *career* ahead of *calling* on *carreira*'s card.
- `docs/` describes both inputs (`docs/guides/rebuild_corpus.md`, the lexicon library notes).
