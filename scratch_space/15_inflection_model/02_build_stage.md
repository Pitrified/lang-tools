---
status: done
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
  speech: the commonest class of the copied senses; source `transform.SOURCE_INFLECTION`, a new
  tag), and copy each base sense of that class with the form note (a person-noun feminine copies
  the `noun.person` senses only). Count forms and senses added.
- `propagate_base_pins`, after `apply_best_senses`: a model form whose base has a pinned sense
  takes the pin on the same concept. `apply_pinned_part_of_speech` then runs as now.
- Manifest: an `inflections` block with the floor and the counts (no table, so no extract date).
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

## What the implementation found

- `apply_inflections` and `propagate_base_pins` in `ingestion/inflections.py`, wired into
  `build_initial`; a new provenance tag `inflection`; 4 stage tests. The plan's
  `apply_inflections(tables, rows, zipf_by_form)` became `apply_inflections(tables, zipf=...)`,
  since there are no rows. The topic test of `test_pipeline.py` now also finds *casas*.
- Rebuild: 12,395 pt forms (the measure's count) with 49,675 senses, 444 pins from their base;
  zero stale rows anywhere. Gate PASS. pt lemmas 46,194 -> 58,589, pt senses 66,526 -> 116,201,
  pt cards with a form note 419 -> 12,814. pt cards by band: A1 789 -> 996, A2 778 -> 1,445,
  B1 1,377 -> 3,031, B2 1,284 -> 2,864, C1 1,526 -> 3,327, C2 40,387 -> 46,873. Other languages
  unchanged.
- One look-alike row that was stale now applies (6,839 -> 6,840 edges), since it names a pt form
  the build now has; 5 more lemmas take a pinned part of speech (90 -> 95).
- The seed grows from 587 to 863 lemmas (276 forms) and 660 to 1,000 senses; `make check` 551.
- `02.1_check_forms.py` on all 12,395: the card is the base's card for 12,234; for 147 the base's
  card is of another class and the form gets a sense of its own class, which is better than the
  base's card (*cercas* "fence", where *cerca*'s card is "approximately"; *chamas* "fire"); 14
  differ through a tie (*chegadas* "advent" against *chegada* "arrival", *solteiros* "bachelor"
  against "unmarried").
- Read 100 of a 500 sample by eye: the base and note right on all but *virei* (the future of
  *vir*; in speech mostly *virar* "I turned"), *obvio* (a misspelling of *óbvio*, read as
  *obviar*) and *rebelo* (mostly a name). Three glosses are wrong because the base's card is
  (*gorduras* "soil, dirt", *troncos* "belly", *pintadas* "paved"): a form shows its base's card
  by design, so a card review of the base fixes both.
- The 498 forms with a sense of their own in kaikki are in
  [`02.2_own_word_forms.md`](02.2_own_word_forms.md) (Q7 a).
- Until phase 3, the forms are cards and translations (Q9).
