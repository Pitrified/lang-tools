# Phase 1 - freeze the lang-tools library API

## Overview

Lock down the importable surface of `lang-tools` and the on-disk content layout
**in place** (still one repo, no extraction yet). This is the cheap Python
interface that both the repo split (phase 2) and the HTTP read API (phase 3)
depend on. Iterating it here, in-process, is far cheaper than churning a
cross-repo or network contract later.

Context: [`00-start.md`](00-start.md).

## Goals

1. Decide and freeze the public library API `lang-tutor` will import:
   `Word` + the sentence/conversation content models, the read/query helpers
   (`get_words_filtered`, `get_word_by_id`, sentence/conversation lookups), the
   `language/` presets, and the content-producing LLM chains (`translation`,
   `conversation`, `splitter`, `word_generator`, `topics`, `greeting`).
2. Define the LFS content layout: words file(s) + sentences/conversations
   file(s), per-language, that the word store reads from the cloned working
   tree. Confirm git-lfs is tracking them.
3. Confirm content is **not** bundled into the wheel (kept as repo data read
   from disk, not package-data).

## Plan

- Audit current imports of `words/`, `language/`, `progress/`, `llm/` to map the
  real consumed surface vs. internal helpers.
- Promote the intended-public names into a stable `__init__` export list; mark
  everything else as internal. No behaviour change, just a frozen façade.
- Settle the content directory layout and `.gitattributes` LFS tracking globs.
- Document the frozen API (what tutor may import) at the top of this folder or
  in `docs/library/`, so phase 2 has a contract to code against.

## Out of scope

- No extraction to `lang-tutor` yet (phase 2).
- No HTTP endpoints (phase 3).
- `progress/` and `llm/tutor.py` are tutor-side; they move in phase 2 and only
  need their *dependencies* on the frozen API to be stable here.

## Done when

- The export list `lang-tutor` will import is fixed and documented.
- The LFS content layout is defined and tracked.
- `uv run pytest && uv run ruff check . && uv run pyright` pass.
