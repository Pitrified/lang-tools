---
status: in progress
---

# Phase 2 - Rulebook and harness

## Overview

The review harness, in the unranked review's shape, with two batch kinds.
Context: [`00_start.md`](00_start.md), depends on [`01_build_inputs.md`](01_build_inputs.md).

## Goals

1. Worklists:
   - members: every card meaning with two or more pt words (7,723), each word with its level,
     the en gloss, the en and it words, and rule hints (plural of, feminine of, capitalised,
     four or more words);
   - leads: the 353 cards led by an en -ing form of an en verb, with the concept's en words in
     their current order.
2. A rulebook in `docs/guides/` and a skill in `.claude/skills/`, its hash on every row.
3. `serve`, `apply` with validation, `status`, over `ingestion.review_batches`.
4. Verdicts written to the phase 1 inputs and to `member_form_drops.jsonl`.

## Plan

- Member verdicts per word: keep; form of a named base (plural or adjective feminine); drop
  (wrong meaning, a definition, a misspelled or capitalised duplicate).
- Lead verdicts per card: keep the lead, or name the word that should lead.
- Batch sizes chosen so a batch matches the 21_unranked_pt_words batch in tokens: about 100
  meanings or 100 cards.
- A shadow log, as the other reviews keep, so a re-review can be compared.

## Out of scope

- Running batches beyond a smoke batch (phases 3 and 4).

## Done when

- `make check` passes; a smoke batch of each kind is served, filled by hand and applied.
- The guide and the skill are in `docs/` and `.claude/skills/`.
