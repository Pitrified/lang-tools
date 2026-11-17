---
status: draft
---

# Phase 5 - Rebuild and release

## Overview

Rebuild with the reviewed rows, measure, release, and hand acerta a new asset.
Context: [`00_start.md`](00_start.md), depends on [`04_full_run.md`](04_full_run.md).

## Goals

1. A rebuild; the checks C1, C2, C3, C6, C7 and C8 re-run, with before and after counts.
2. The quality gate passes, including "definition == lemma".
3. Release 0.10.0 with its changelog; acerta's card and meanings assets re-exported on an
   acerta branch.

## Done when

- The counts are logged, `make check` passes, the tag is local for the user to push.
