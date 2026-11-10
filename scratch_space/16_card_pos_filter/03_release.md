---
status: done
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

## What the implementation found

- The local uv (0.13.1) writes lock revision 5; the pre-commit hook pins uv 0.9.16, which writes
  revision 3. The release lock was set back to 3, and the hook passed.
- lang-tutor sends only the `CardQuery` fields that differ from their defaults
  (`content/http.py` `_card_params`), so 8010 applies its own default: the four drill queries,
  500 cards each by frequency and by two random seeds, drew no function word.
- That encoder turns an empty list into no pair at all, so a lang-tutor query with
  `exclude_part_of_speech=[]` reaches 8010 as the default and still gets no function word
  (0 against 123 when 8010 is sent `?exclude_part_of_speech=` directly). No lang-tutor query
  sets it today; the fix belongs in lang-tutor, sending the bare key for an empty list.
- The sentence drill finds 4 pt cards at B1 with or without the filter: its pool is small
  because of the example filters, not this change.
