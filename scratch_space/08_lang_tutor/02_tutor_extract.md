# Phase 2 - extract tutor concerns into lang-tutor (library-coupled)

## Overview

Stand up the new `lang-tutor` repo and migrate all learner-facing, per-user,
interactive concerns out of `lang-tools`. In this phase `lang-tutor` depends on
`lang-tools` as a **library** and reads content via in-process query helpers -
**no HTTP boundary yet**. This proves the split works while the interface under
test is still a cheap Python API (phase 3 swaps the transport).

Context: [`00-start.md`](00-start.md), depends on
[`01_lib_freeze.md`](01_lib_freeze.md).

## Goals

1. Scaffold `lang-tutor` from `python-project-template`, reusing the same
   Params/Config/Singleton patterns.
2. Add `lang-tools` as a dependency (`lang-tools @ git+https://.../@<tag>`),
   importing the frozen API from phase 1.
3. Migrate, in order of increasing coupling:
   1. `exercises/` (five mechanics + round/result protocol) - no LLM dependency.
   2. `progress/` (`UserWordProgress`, weighted `select_words`) - per-user.
   3. `llm/tutor.py` + `webapp/services/tutor_service.py` (the live tutor loop).
   4. `webapp/` (pages, runtime exercises API, OAuth, user service, session
      state).
4. Wire exercise/word selection to read the pool from `lang-tools` query helpers
   in-process.

## Plan

- Move `exercises/` + `progress/` first and get their tests green in the new
  repo - this validates the cross-repo import with the lowest-risk code.
- Then move the tutor chain + service, then the webapp.
- Delete the migrated modules from `lang-tools` once `lang-tutor` is green, so
  there is a single source of truth. Keep the one-way dependency:
  `lang-tools` must never import `lang-tutor`.

## Out of scope

- HTTP read API and switching content access to the network (phase 3).
- Content-producing LLM chains stay in `lang-tools` (data production).

## Done when

- `lang-tutor` runs the full exercise + tutor flow, sourcing content from
  `lang-tools` in-process.
- Migrated modules removed from `lang-tools`; no `lang-tutor` import leaks back.
- Both repos pass `uv run pytest && uv run ruff check . && uv run pyright`.
