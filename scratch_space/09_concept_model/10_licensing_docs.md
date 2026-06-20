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

> **From the 5.5 cleanup (2026-06-20).** The CC-BY-SA open question below is **resolved**:
> kaikki is dropped (decided 2026-06-18, executed in [`05.5_cleanup.md`](05.5_cleanup.md)),
> so there is no share-alike source to isolate. The shipped posture is permissive-OMW
> (verify per lexicon - the brainstorm's blanket "Apache-2.0" is wrong) + CC0 Wikidata
> (optional) + CC-BY Tatoeba (examples) + a new permissive CILI English-gloss fallback
> (`source=cili`), with **no CC-BY-SA anywhere** and an attribution-only dataset card. This
> phase then only verifies per-source licenses and writes the card.

## What this phase will cover

- **License decision** - **settled by the 5.5 cleanup**: drop kaikki/Wiktionary text
  (option (c)/drop), leaving a clean permissive + CC0 + CC-BY stack with no share-alike.
  This phase records it rather than choosing it. Any future kaikki use stays
  license-isolated or routes through an LLM rewrite so the shipped text is original.
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
