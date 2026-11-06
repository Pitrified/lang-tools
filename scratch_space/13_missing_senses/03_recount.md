---
status: draft
---

# Phase 3 - rebuild and re-count

## Overview

Rebuild with the new rows and measure the result on the same items as phase 2.
Context: [`00_start.md`](00_start.md), "Measurement". Depends on [`02_review.md`](02_review.md).

## Plan

- Rebuild (`docs/guides/rebuild_corpus.md`), run the gate, note the additions applied and stale.
- One more agent review of the same 1,000 cards, same rules, for the after table; it writes no
  curated row unless it finds a new error, which is then labelled and applied as in phase 2.
- Recount the stale look-alike rows (34 on 2026-11-06; the 28 on removed lemmas should mostly
  re-attach).
- Restart the 8010 API on the new corpus.

## Done when

- Gate PASS; the before and after tables sit side by side here; each card still wrong has its
  reason.

## What the implementation found
