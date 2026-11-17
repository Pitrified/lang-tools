---
status: done
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

## What the implementation found

- One module, `ingestion.meaning_review`, and one CLI serve both kinds, told apart by the batch
  prefix (`w` meanings, `l` leads); one rulebook, `docs/guides/meaning_review.md`, and one
  skill, `meaning-review`.
- The worklists start from the 19,599 drill cards (7 s over the store): 7,743 meanings with two
  pt words or more, and 207 lead meanings (the 353 -ing cards share meanings, and those with no
  other en word are left out).
- An `f` label is checked against the inflection rules (`form_of`), so a form the rules do not
  make is refused rather than given a made-up note.
- Leads are logged in the review log like the members; a `k` writes no lead row, so the
  frequency order stays.
- Not built, for now: a re-check command and a shadow log. Neither has a case yet; the pilot
  decides.
- The smoke run found a real bug: a store built from a corpus older than `Sense.is_lead` read
  NULL and every sense read failed. `codec.model_from_row` now gives such a field its default,
  with a test; the phase 1 tests had missed it because they build a fresh corpus.
- Smoke batches `w0001` (5 meanings, 16 words: 13 k, 1 f *resinas*, 2 d *pre-escolar*,
  *agravamento*) and `l0001` (5 meanings: *informative* leads *informativo*) applied.
  `l0001` item 5 showed a gap: *escotilha* (a ship's hatch) is the only pt word of "the
  production of young from an egg", and a meaning with one pt word is in no worklist (Q5).
