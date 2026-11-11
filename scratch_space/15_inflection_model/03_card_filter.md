---
status: planned
---

# Phase 3 - card filter for forms

## Overview

Keep the inflected forms out of card queries unless a query asks for them (Q2 b).
Context: [`00_start.md`](00_start.md) Q2; depends on [`02_build_stage.md`](02_build_stage.md).
If Q2 is answered a, this phase is discarded.

## Goals

1. `CardQuery.include_forms: bool = False`; `lemma_store._card_where` adds
   `d.form_note IS NULL` unless it is set.
2. The sense-review worklist keeps the forms, as it keeps the function words.
3. Docs: `docs/library/lexicon.md`, `docs/library/frozen_api.md`, the `card.py` module docstring.

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
