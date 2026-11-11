---
status: done
---

# Phase 3 - card filter for forms

## Overview

Keep the inflected forms out of card queries unless a query asks for them (Q2 b), and out of
every list of a concept's words (Q9 a).
Context: [`00_start.md`](00_start.md) Q2, Q9; depends on [`02_build_stage.md`](02_build_stage.md).

## Goals

1. `CardQuery.include_forms: bool = False`; `lemma_store._card_where` adds
   `d.form_note IS NULL` unless it is set.
2. The sense-review worklist leaves the forms out (the default; corrected at review, see below).
3. Q9 a: no form in a card's translations or own-language synonyms, in the `require_translation`
   check, in `lemmas_for_concept`, or in a hydrated concept's `lemmas`.
4. Docs: `docs/library/lexicon.md`, `docs/library/frozen_api.md`, the `card.py` module docstring.

## Plan

- The field, the clause, the worklist query (`sense_review.build_worklist`), tests in
  `tests/lexicon/test_lemma_cards.py` and `tests/webapp/test_cards_api.py` (a bool round-trips in
  a query string, unlike an empty list).
- On 8010: the four lang-tutor drill queries (scratch `drill_fw_check.py` pattern) return no
  form card by default; `include_forms=true` returns them.

## Out of scope

- Any lang-tutor change; it gets the default with the pin bump.

## Done when

- The filter holds on 8010, `make check` and the docs build pass.

## What the implementation found

- Review at the start: the worklist line was wrong. The reviewed forms were in the worklist, but a
  model form's card is its base's card, so reviewing the base reviews the form; the worklist now
  takes the default and leaves every form out. Q9 was folded in.
- `CardQuery.include_forms` (`d.form_note IS NULL` unless set), the translations and
  `require_translation` queries, `lemmas_for_concept` and `hydrate_concept` leave out a sense
  with a form note; `senses_for_concept` and the concept's `senses` keep every edge. `_card_where`
  went over the complexity limit, so its yes/no filters became a table. 3 tests; `make check` 554.
- On 8010: en "year" lists pt `['ano']` (was `['anos', 'ano']`), "be" `['ser', 'estar']` (was 26
  words). lang-tutor's four drill queries through its client, by frequency and two seeds: no form
  card, no function word. Wordle has 393 cards (472 on v0.6.0) and diacritic typing 371 (414): the
  difference is the reviewed forms of `14_number_modal_words`, now left out like every form. The
  5-letter B1 query with `include_forms=true` returns 500 cards, 271 of them forms.
- lang-tutor's encoder sends only non-default fields, so it gets the default with no change, and
  can ask for forms once it sets the bool.
