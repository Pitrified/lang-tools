---
status: done
---

# Phase 2 - function-word filter

## Overview

`CardQuery.exclude_part_of_speech`, a list of classes left out (Q1 b), whose default is the four
function-word classes (Q2 a), so lang-tutor's drills lose them with no change there.
Context: [`00_start.md`](00_start.md) Q1, Q2, Q5; after phase 1, so *um* and *uma* are caught.

## Plan

- `FUNCTION_WORD_POS` (`pronoun`, `determiner`, `preposition`, `conjunction`) defined once in
  `lexicon.card`, next to the filter (the core model does not import from `ingestion`, where
  `LEXFILE_POS` lives); `CardQuery.exclude_part_of_speech: list[str]` defaults to it, and
  `lemma_store._card_where` adds `d.part_of_speech NOT IN (...)`. A lemma with no part of speech
  is kept (`NOT IN` drops a NULL, so the clause allows it explicitly).
- An empty value turns the exclusion off (Q5 b): `?exclude_part_of_speech=` arrives as `[""]`,
  which a validator turns into `[]`. A query for one function class sends both keys
  (`?part_of_speech=pronoun&exclude_part_of_speech=`), as the docs say; without the second it
  returns nothing.
- The sense-review worklist (`sense_review.build_worklist`) builds its own `CardQuery`; it
  passes an empty list, so a review still serves the function-word cards.
- The read API takes it from the query string with no router change (`CardQuery` is the query
  model); a webapp test.
- Docs: `docs/library/frozen_api.md` (the surface change), the cards narrative.
- Check on 8010: a pt drill query returns no function word with the default, and the empty value
  returns them (127 pt lemmas expected after phase 1).

## Done when

- The filter works over the API, tests, gate and `make check` pass, docs build.

## What the implementation found

- Plan review: the sense-review worklist builds its own `CardQuery` and would have lost the
  function words silently; it now passes an empty list. `FUNCTION_WORD_POS` went to
  `lexicon.card`, as the core model does not import from `ingestion`.
- The clause keeps a lemma with no part of speech (`IS NULL OR NOT IN`); a validator drops the
  empty string a bare `?exclude_part_of_speech=` sends. Tests: the store (default, empty list,
  one class with both fields, no class kept) and the read API (a listed class left out, the
  empty value).
- On 8010, the full corpus: the 500 most frequent pt cards hold 0 function words by default and
  104 with the empty value (*de*, *do*, *em*, *eu* first). A query for one class with both keys
  returns 123 lemmas (12 conjunctions, 53 determiners, 35 prepositions, 23 pronouns), 0 without
  the empty value. The 4 short of 127 are *a*, *o*, *e*, *à*: one-letter lemmas are never cards.
- `make check` 472 passed, docs build.
