# implementation tracking

Clean the words of a meaning and their order, found from acerta's word page and phone use:
pt plurals and adjective feminines stored beside their base, wrong or definition-like pt
words, cards led by a wrong -ing translation, and the pt glosses equal to their word. Claude
subagents review under a rulebook; the build re-applies the curated rows. Analysis, the
proposed checks and decisions in [`00_start.md`](00_start.md).

## Key decisions

- A plural or adjective feminine beside its base becomes a form of it, with a form note,
  not a drop (Q1).
- A wrong lead translation is fixed by a reviewed lead row per card meaning, not by a ranking
  rule (Q2).
- The wrong-member review reads every card meaning with two or more pt words, 7,723, in waves
  over several sessions (Q3).
- The it cognate gap is parked in `open_points.md` (Q4).

## Phases

| #  | Phase                       | Plan                                         | Status  |
| -- | --------------------------- | -------------------------------------------- | ------- |
| 1  | Curated inputs in the build | [`01_build_inputs.md`](01_build_inputs.md)   | done |
| 2  | Rulebook and harness        | [`02_harness.md`](02_harness.md)             | done |
| 3  | Pilot of 500+               | [`03_pilot.md`](03_pilot.md)                 | draft   |
| 4  | The rest, in waves          | [`04_full_run.md`](04_full_run.md)           | draft   |
| 5  | Rebuild and release         | [`05_rebuild.md`](05_rebuild.md)             | draft   |

Status values: draft / planned / in progress / done / superseded / discarded.

## Log

Append-only. Newest at the bottom.

- 2026-11-17 : bootstrapped from the open points "Translations ranked by an inflated -ing
  frequency" and "Plural and wrong pt members of a meaning", with "pt gloss equal to its
  word"; measured thirteen candidate checks read-only on the 0.9.0 build and acerta's
  meanings asset; the user picked C1 to C4 and C6 to C8, answered Q1 to Q4; the it cognate
  gap parked as an open point.
- 2026-11-17 : phase 1 review before code: forms need no new input, a `sense_additions` row
  on an existing link only sets its form note (how *são* got its note), so phase 1 is the lead
  pin and the gloss rows; the lead copies `Sense.is_best` (field, codec column, cache v11,
  card order); `lemmas_for_concept` has no order and acerta orders a meaning's words itself,
  so its export reads `is_lead` at the phase 5 re-export.
- 2026-11-17 : phase 1 - `Sense.is_lead` (codec column, cache v11) set by the new
  `ingestion.lead_translations` stage from `lead_translations.jsonl`, keyed on concept and
  language; the card translations put the lead first after `_rank_translations`; build
  manifest `lead_translations`; library notes, frozen API and changelog updated. Found ten pt
  glosses equal to their word, not five; ten `gloss_overrides.jsonl` rows written `proposed`.
  `make check` 589 passed, docs build strict. Waits on the user accepting the gloss rows.
- 2026-11-17 : phase 1 closed: the user accepted the ten gloss rows.
- 2026-11-17 : phase 2 - `ingestion.meaning_review` with `meaning_review_cli`, the rulebook
  `docs/guides/meaning_review.md` and the `meaning-review` skill; worklists 7,743 meanings and
  207 leads; `make check` 599 passed. The smoke run found and fixed a codec bug (a store from a
  corpus older than `is_lead` failed on NULL). Smoke batches w0001 and l0001 applied. Raised Q5:
  meanings with one pt word, such as *escotilha* on hatching, are in no worklist.
