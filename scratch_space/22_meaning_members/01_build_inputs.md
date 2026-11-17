---
status: done
---

# Phase 1 - Curated inputs in the build

## Overview

The review needs somewhere to write that the build already reads. Drops have one
(`member_form_drops.jsonl`), and so do forms: a `sense_additions.jsonl` row on a link the build
already has only sets that sense's form note (`apply_sense_additions`), which is how *são* on
"be" got its note. A lead translation has none. This phase adds it, and the C8 gloss fixes,
so a pilot row can be checked end to end by a rebuild.
Context: [`00_start.md`](00_start.md).

## Goals

1. A reviewed lead row (concept, language, lemma) that puts that word first in a card's
   translations, and is on the sense for other readers (acerta's export orders a meaning's
   words itself, from `senses_for_concept`).
2. `gloss_overrides.jsonl` rows for the pt glosses equal to their word (C8).
3. Tests showing that a form-note sense addition on an existing link hides the word from
   the cards and the concept's word list, since phase 2 relies on it for Q1.

## Plan

- Lead rows: `Sense.is_lead`, set by a reviewed `lead_translations.jsonl`, in the shape of the
  best-sense pin (`Sense.is_best`, `best_senses.jsonl`): a field with a default, a codec column,
  a store cache version bump (`CACHE_VERSION` 11), and the lead moved first in
  `_card_translations` after `_rank_translations`. `lemmas_for_concept` has no order today and keeps
  none. Keyed on `concept_key` and `language`, latest row wins, so a concept has at most
  one lead per language; a row with no `lemma_id` retracts, as a best-sense row with no
  concept does. The field is an addition to the frozen surface, noted in
  `docs/library/frozen_api.md`.
- Counted in the build manifest, like the other curated inputs.
- Tests on the bootstrap seed: the loader, the retraction, the card order.
- The gloss rows, written by hand from the en glosses.

## Out of scope

- The review harness and any review rows beyond test fixtures (phase 2).
- A rebuild of the full corpus (phase 5).

## Done when

- `make check` passes with the new tests.
- A fixture form row hides a plural from its meaning's word list and cards; a fixture lead
  row puts a lower-frequency word first on a card.
- `docs/` describes the new input (the lexicon library notes' curated-file table and the
  card translations, the frozen API).

## What the implementation found

- Ten concepts have a pt gloss equal to one of their pt words, not five: the dump's four, *jogar
  dados*, and five multiword ones (*de qualquer maneira*, *mulher negra*, *isópodes*, *de
  maneira nenhuma*, *ler superficialmente*). All ten rows were written `proposed`; the user
  accepted them.
- The forms test already existed: `test_an_existing_link_only_takes_the_form_note`
  (sense additions) and `test_a_form_is_never_a_translation_or_a_member` (store).
- `_rank_translations` moves phrases and symbols after the words, so the lead is put first
  after the ranking, not in the SQL order; a lead phrase still leads.
- The store cache moves to v11, so the next `make serve` rebuilds `_store.sqlite` from the
  Parquet once.
- `docs/library/frozen_api.md` and `CHANGELOG.md` call `is_lead` unreleased until phase 5
  names the version.
