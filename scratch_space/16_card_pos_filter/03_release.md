---
status: in progress
---

# Phase 3 - release v0.6.0

## Overview

Release lang-tools and bump lang-tutor's pin, as for v0.5.0
([`14_number_modal_words/08_release.md`](../14_number_modal_words/08_release.md)).
Context: [`00_start.md`](00_start.md).

## Plan

- CHANGELOG, version 0.6.0, release commit, `--no-ff` merge into main, annotated tag; the user
  pushes.
- lang-tutor: pin bump on a short branch cut from its main (check first that no running server
  depends on files of another branch), `uv lock`, `make undev`, `make check`; its four queries need
  no change, since the default excludes the function words (Q2 a). Restart 8000.

## Done when

- lang-tutor runs on the new tag, its drills draw no function word, and `make check` passes in
  both repos.
