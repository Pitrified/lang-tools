---
status: draft
---

# Phase 2 - function-word filter

## Overview

The card query filter that leaves out the function words, in the shape and default of Q1 and Q2.
Context: [`00_start.md`](00_start.md) Q1, Q2; after phase 1, so *um* and *uma* are caught.

## Plan

- The field on `CardQuery` and its clause in `lemma_store._card_where`; the function-word
  classes defined once, next to `LEXFILE_POS`.
- The read API takes it from the query string with no router change (`CardQuery` is the query
  model); a webapp test.
- Docs: `docs/library/frozen_api.md` (the surface change), the cards narrative.
- Check on 8010: a pt drill query returns no function word with the default, and `only` (if
  chosen) returns the 127.

## Done when

- The filter works over the API, tests, gate and `make check` pass, docs build.
