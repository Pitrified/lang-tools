---
status: done
---

# Phase 4 - release v0.4.0

## Overview

Release lang-tools and bump lang-tutor's pin, as for v0.3.0 (lang-tutor
`03_ui_followups/05_lang_tools_release.md`). Context: [`00_start.md`](00_start.md) Q6, Q7.

## Plan

- CHANGELOG entry, version 0.4.0 in `pyproject.toml` and `uv.lock`, release commit, `--no-ff`
  merge of `feat/13_missing_senses` into main, annotated tag; the user pushes.
- In lang-tutor: bump the pin, `uv lock`, `make undev` if needed, `make check`, restart the 8000
  server. Showing `form_note` on its cards is lang-tutor work and needs the user's go-ahead
  there (Q7).

## Done when

- lang-tutor runs on the new tag, and `make check` passes in both repos.

## What the implementation found

The user pushed main, the branch and the tag. lang-tutor took the bump on its own branch,
`deps/lang-tools-v0.4.0`, since it was on main; its lock already uses revision 5, so only the
lang-tools lock needed the revision kept at 3. lang-tutor `make check` passes (148 tests) and
the 8000 server runs on v0.4.0 against the 8010 corpus. `form_note` on lang-tutor's cards is
still open there (Q7).
