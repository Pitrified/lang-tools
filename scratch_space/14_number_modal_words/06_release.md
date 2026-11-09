---
status: planned
---

# Phase 6 - release v0.5.0

## Overview

Release lang-tools and bump lang-tutor's pin, as for v0.4.0
([`13_missing_senses/04_release.md`](../13_missing_senses/04_release.md)).
Context: [`00_start.md`](00_start.md).

## Plan

- CHANGELOG entry, version 0.5.0 in `pyproject.toml` and `uv.lock` (lock revision kept at 3),
  release commit, `--no-ff` merge into main, annotated tag; the user pushes.
- lang-tutor: bump the pin on a short branch, `uv lock`, `make undev`, `make check`, restart
  the 8000 server.

## Done when

- lang-tutor runs on the new tag, and `make check` passes in both repos.
