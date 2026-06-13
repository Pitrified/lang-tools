# Phase 3 - lang-tools HTTP read API + switch lang-tutor to HTTP

## Overview

Add the content-serving HTTP surface to `lang-tools` and switch `lang-tutor`
from in-process library reads to consuming content over HTTP. The repo split is
already stable (phase 2), so this phase changes only the **transport**, not the
content contract - one hard change, isolated.

Context: [`00-start.md`](00-start.md), depends on
[`02_tutor_extract.md`](02_tutor_extract.md).

## Goals

1. Add a read API to `lang-tools`: filtered word lookups, word-by-id, and
   sentence/conversation fetch (the surface frozen in phase 1, exposed over
   HTTP).
2. Define the client `lang-tutor` uses to call it, behind the same interface it
   already imports - so swapping in-process reads for HTTP is a single seam.
3. Document the operator setup: clone `lang-tools` with the git-lfs binary
   installed (else pointer stubs), then run/deploy the service. Content is
   public, so no auth/token.

## Plan

- Implement the read endpoints reusing the query helpers from phase 1 (the
  service is a thin HTTP layer over them; no new content logic).
- In `lang-tutor`, introduce a content-source abstraction with two
  implementations: the existing in-process reader and a new HTTP client. Switch
  the default to HTTP; keep in-process available for local/dev.
- Keep content out of the wheel; the service reads it from the cloned working
  tree.

## Out of scope

- Per-user progress and session state stay in `lang-tutor` (mutable, not LFS).
- No write endpoints; this is a read/content-distribution API.

## Done when

- `lang-tools` serves words/sentences over HTTP from the LFS-materialised tree.
- `lang-tutor` runs the full flow against the HTTP content source.
- Operator setup (git-lfs + run service) is documented.
- Both repos pass `uv run pytest && uv run ruff check . && uv run pyright`.
