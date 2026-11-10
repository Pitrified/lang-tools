---
status: draft
---

# Phase 2 - function-word filter

## Overview

`CardQuery.exclude_part_of_speech`, a list of classes left out (Q1 b), whose default is the four
function-word classes (Q2 a), so lang-tutor's drills lose them with no change there.
Context: [`00_start.md`](00_start.md) Q1, Q2, Q5; after phase 1, so *um* and *uma* are caught.

## Plan

- `FUNCTION_WORD_POS` (`pronoun`, `determiner`, `preposition`, `conjunction`) defined once, next
  to `LEXFILE_POS`; `CardQuery.exclude_part_of_speech: list[str]` defaults to it, and
  `lemma_store._card_where` adds `d.part_of_speech NOT IN (...)`. A lemma with no part of speech
  is kept (`NOT IN` drops a NULL, so the clause allows it explicitly).
- An empty value turns the exclusion off (Q5 b): `?exclude_part_of_speech=` arrives as `[""]`,
  which a validator turns into `[]`. A query for one function class sends both keys
  (`?part_of_speech=pronoun&exclude_part_of_speech=`), as the docs say; without the second it
  returns nothing.
- The read API takes it from the query string with no router change (`CardQuery` is the query
  model); a webapp test.
- Docs: `docs/library/frozen_api.md` (the surface change), the cards narrative.
- Check on 8010: a pt drill query returns no function word with the default, and the empty value
  returns them (127 pt lemmas expected after phase 1).

## Done when

- The filter works over the API, tests, gate and `make check` pass, docs build.
