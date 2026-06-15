---
status: draft
---

# Phase 10 - licensing & packaging

> Draft. Scope sketch to hold the overarching story; not yet the plan of record.

## Overview

Make the dataset shippable as a **free and open-source** resource: settle the
license, record attribution for every source, and document the whole thing. This
is the closing phase that turns the working data into something publishable.
Context: [`00-concepts-brainstorm.md`](00-concepts-brainstorm.md), "Licensing -
free and open dataset". Depends on the source mix being final (phases 5-7).

## What this phase will cover

- **License decision** - the core (OMW, Apache-2.0; `wordfreq`, MIT) is
  permissive. The open question is the CC-BY-SA Wiktionary enrichment: choose
  among (a) isolate it in a separately-licensed layer with attribution, (b) accept
  CC-BY-SA for the whole dataset as an acceptable open license, or (c) drop
  Wiktionary text and use it only to guide freshly-written LLM glosses. Decide and
  record.
- **Per-source attribution** - confirm and document the license of each input,
  including per-list frequency sources (SUBTLEX/OpenSubtitles) and CEFR graded
  lists, which must be license-checked individually before shipping.
- **Dataset card** - a card recording each source, its license, required
  attribution, coverage (languages, counts), and the estimated-vs-sourced share
  of frequency/CEFR values.
- **Project docs** - update `docs/` (library narrative for the new lexical model,
  guides for ingestion/maintenance, API reference via docstrings) per repo
  convention; ensure `mkdocs` builds.
- **Distribution shape** - how the dataset is published/versioned (git-LFS layout
  from phase 3, release tagging), if publishing externally.

## Out of scope

- Generating or maintaining the data (phases 5, 8); model/store changes.

## Done when (draft)

- License chosen and applied; dataset card and docs complete and building;
  attribution verified for every shipped source.
- `uv run pytest && uv run ruff check . && uv run pyright` and `uv run mkdocs
  build` pass.
