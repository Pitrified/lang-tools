---
status: done
---

# Phase 8 - release v0.5.0

## Overview

Release lang-tools and bump lang-tutor's pin, as for v0.4.0
([`13_missing_senses/04_release.md`](../13_missing_senses/04_release.md)).
Context: [`00_start.md`](00_start.md). After phases 6 and 7.

## Plan

- CHANGELOG entry, version 0.5.0 in `pyproject.toml` and `uv.lock` (lock revision kept at 3),
  release commit, `--no-ff` merge into main, annotated tag; the user pushes.
- lang-tutor: bump the pin on a short branch, `uv lock`, `make undev`, `make check`, restart
  the 8000 server.

## Done when

- lang-tutor runs on the new tag, and `make check` passes in both repos.

## What the implementation found

- lang-tutor's lock resolves the git tag on GitHub, so the pin bump waits for the push; the
  checks ran first against an editable install of the local tag, then on the pinned one.
- Switching the lang-tutor checkout to cut the bump branch takes templates and static files
  of an unmerged branch off disk, under a running server; the bump branch was cut after
  `feat/form_note` was merged into lang-tutor main instead.
- lang-tutor draws cards at random, weighted by CEFR level, with no filter on part of speech,
  so the closed-class cards of phase 7 now reach its drills.
