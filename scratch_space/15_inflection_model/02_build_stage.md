---
status: planned
---

# Phase 2 - build stage

## Overview

Apply the form table at build, so a rebuild gives every frequent pt form a lemma on its base word's
meaning.
Context: [`00_start.md`](00_start.md) Q3, Q5, Q7; depends on
[`01_form_table.md`](01_form_table.md).

## Goals

1. `apply_inflections` in `build_initial`, after the sense additions and before `enrich`.
2. A form's card is its base's card: pins propagate.
3. Before and after counts, and a check of the model forms against their bases.

## Plan

- `apply_inflections(tables, rows, zipf_by_form)`: for each form at or above the floor (Q3), not
  a closed-class word (`closed_class.CLOSED_CLASS`), not a lemma of the build (Q5 a), whose picked
  base the build has with at least one sense of the form's class: create the lemma (part of
  speech from the form's class, source `SOURCE_KAIKKI` or similar, checked against
  `transform.SOURCE_*`), and copy each base sense of that class with the form note. Count forms
  added, senses added, and the forms skipped by reason.
- `propagate_base_pins`, after `apply_best_senses`: a model form whose base has a pinned sense
  takes the pin on the same concept. `apply_pinned_part_of_speech` then runs as now.
- Manifest: an `inflections` block with the counts and the table's extract date.
- Tests on in-memory tables: a plural, a verb form with a noun-and-verb base (only the verb senses
  copied), a form the build already has (left alone), a pinned base.
- Rebuild, gate, `make check`; restart 8010.
- Check (scratch `02.1_check_forms.py`), on every model form and in detail on a random 500: the
  form's card concept equals its base's card concept, the note names the base, the part of speech
  is the form's class. Read 100 of the 500 cards by eye on 8010. List the Q7 forms (a word of
  their own) in a side document.
- Counts before and after: pt lemmas, senses, cards by CEFR band, look-alike worklist size
  (mining reads lemmas, the built edges cannot move).

## Out of scope

- The card filter (phase 3); until it lands, the new forms are cards.

## Done when

- The rebuild applies the stage with zero errors, the gate passes, every check holds or each
  exception is explained, and `make check` passes.
