---
status: planned
---

# Phase 1 - rename `Word` to `Lemma`

## Overview

A preliminary, purely mechanical refactor that renames the central lexical
entity from `Word` to `Lemma` (the literature term - WordNet, OntoLex-Lemon,
BabelNet) and the package from `lang_tools.words` to `lang_tools.lexicon`. No
behaviour changes, no model reshaping - that is phase 2. Doing it first means
every later phase is written in the target vocabulary and we never refactor the
same names twice. Context: [`00-concepts-brainstorm.md`](00-concepts-brainstorm.md),
"Naming: `Lemma`, not `Word`".

It spans two repos that move in lockstep (both ours): the `lang-tools` producer
and the `lang-tutor` consumer, including the HTTP surface between them. There is
no external contract to preserve, so the rename can be total.

## Goals

1. `Word` -> `Lemma` and `word_id` -> `lemma_id` everywhere, with all derived
   names (`WordExample` -> `LemmaExample`, store helpers, router, tests).
2. Package `lang_tools.words` -> `lang_tools.lexicon`; modules `word.py`,
   `word_id.py`, `word_store.py` -> `lemma.py`, `lemma_id.py`, `lemma_store.py`.
3. `lang-tutor` updated in the same change so the test suites of both repos pass.
4. Zero behaviour change: same fields, same data, same endpoints' behaviour
   (only their paths/names change).

## Plan

### `lang-tools` (producer)

- **Package move**: `src/lang_tools/words/` -> `src/lang_tools/lexicon/`. Keep the
  `ingestion/` subpackage in place under the new package.
- **`word.py` -> `lemma.py`**: rename `class Word` -> `class Lemma`,
  `WordExample` -> `LemmaExample`. Keep `Gloss`, `GlossExample`, `FalseFriend`,
  `FrequencyLevel` as-is (these are not reshaped until phase 2). Update the module
  docstring and the `word_id` import/usage.
- **`word_id.py` -> `lemma_id.py`**: rename `def word_id` -> `def lemma_id`; the
  `w_`-style id prefix is not produced here (ids are bare hex) so nothing changes
  in the hashing.
- **`word_store.py` -> `lemma_store.py`**: rename internals `_ALL_WORDS` ->
  `_ALL_LEMMAS`, `_BY_ID` -> `_LEMMAS_BY_ID`; helpers `get_all_words` ->
  `get_all_lemmas`, `get_word_by_id` -> `get_lemma_by_id`, `get_words_by_language`
  -> `get_lemmas_by_language`, `get_words_by_topic` -> `get_lemmas_by_topic`,
  `get_words_filtered` -> `get_lemmas_filtered`; param `word_id` -> `lemma_id`.
- **`__init__.py`**: update all re-exports and `__all__`, and the module docstring
  (it documents the public surface `lang-tutor` imports).
- **`ingestion/`** (`csv_loader.py`, `dedup.py`, `wiktionary.py`,
  `static_list.py`): update imports and any `Word`/`word_id` references. Behaviour
  unchanged.
- **Webapp**: `routers/words_router.py` -> `lemmas_router.py`; route prefix
  `/api/v1/words` -> `/api/v1/lemmas`, path param `{word_id}` -> `{lemma_id}`,
  handler names `list_words`/`read_word` -> `list_lemmas`/`read_lemma`, `tags`.
  Update `webapp/__init__.py` docstring/import references and wherever the router
  is registered.
- **Bootstrap data** (`data/bootstrap/*.csv`): the header has no `word` column
  (`text,language,part_of_speech,...`), so the CSVs need no change. Confirm the
  loader still finds them under the new package path.
- **Tests**: move `tests/words/` -> `tests/lexicon/`; rename `test_word.py` ->
  `test_lemma.py`, `test_word_id.py` -> `test_lemma_id.py`,
  `tests/webapp/test_words_api.py` -> `test_lemmas_api.py`; update imports,
  symbols, and asserted route paths.

### Decision to confirm before starting

- **`llm/word_generator.py` + `prompts/word_generator/`**: this generates lemma
  candidates. Renaming to `lemma_generator` is consistent with "complete
  coherence" but is adjacent to the model rename. Recommendation: include it in
  this phase (it is the same mechanical class of change) unless we want to keep
  the diff strictly to the data model. Flagged as the one judgment call here.

### `lang-tutor` (consumer)

- Replace `from lang_tools.words.word import Word` -> `from lang_tools.lexicon.lemma
  import Lemma`; type aliases `Word` -> `Lemma` across `progress/selection.py`,
  `content/{base,http,in_process}.py`, `exercises/*`, `progress/*`.
- HTTP client (`content/http.py`): update calls to the renamed endpoints
  (`/api/v1/lemmas`, `{lemma_id}`) and method/param names (`get_word_by_id` ->
  `get_lemma_by_id`, etc.) to match the producer surface.
- `lang-tutor`'s own `webapp/routers/words_router.py` and variable names
  (`word`, `word_id`, `Word.id` docstrings) -> lemma equivalents.
- Update `lang-tutor` tests (imports, fixtures, asserted paths).

### Sequencing

1. Land the `lang-tools` rename on a branch; run its verification suite.
2. Update `lang-tutor` against the new surface; run its verification suite.
3. Land together (or producer first if `lang-tutor` pins a released version -
   confirm how `lang-tutor` depends on `lang-tools`).

## Out of scope

- Any model reshaping: `Concept`, `Sense`, the relation edge tables, dropping
  `translations`/embedded `false_friends` - all phase 2.
- Frequency/CEFR fields (phase 6), storage-format changes (phase 3-4), ingestion
  rework (phase 5). This phase only renames what exists today.

## Done when

- No references to `Word`, `word_id`, `word_store`, or `lang_tools.words` remain
  in either repo except in historical docs/changelogs (grep is clean).
- `uv run pytest && uv run ruff check . && uv run pyright` passes in `lang-tools`.
- `lang-tutor`'s verification suite passes against the renamed surface.
- The webapp serves `/api/v1/lemmas` and `lang-tutor` consumes it end to end.
