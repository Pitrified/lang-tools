# implementation tracking

Sort the pt words wordfreq has no frequency for, with Claude subagents under a rulebook:
drop the misspelled, foreign and malformed ones, give the real ones a commonness bucket the
CEFR score and the card floor can read. Analysis and decisions in [`00_start.md`](00_start.md).

## Key decisions

- Single lowercase words only, 4,814 of the 8,597 (Q3); strays with a frequency later (Q2).
- Bad words are dropped through `member_form_drops.jsonl`; real words get a bucket in a new
  curated file (Q1).
- The harness reuses `ingestion.review_batches` and the sense review's shape.
- A 500-word pilot is read and measured before the rest.

## Phases

| #  | Phase                  | Plan                                     | Status  |
| -- | ---------------------- | ---------------------------------------- | ------- |
| 1  | Rulebook and harness   | [`01_harness.md`](01_harness.md)         | done |
| 2  | Pilot of 500           | [`02_pilot.md`](02_pilot.md)             | planned |
| 3  | The rest               | [`03_full_run.md`](03_full_run.md)       | planned |
| 4  | Buckets in the build   | [`04_build.md`](04_build.md)             | planned |
| 5  | Rebuild and release    | [`05_rebuild.md`](05_rebuild.md)         | planned |

Status values: draft / planned / in progress / done / superseded / discarded.

## Log

Append-only. Newest at the bottom.

- 2026-11-15 : bootstrapped from two open points of `20_rare_words_topics` (on
  `feat/20_rare_words_topics`); measured 8,597 pt lemmas with no frequency, 4,814 single
  words; Q1 to Q3 answered as recommended (drop bad words, bucket real ones; strays later;
  single words only). Phases written. Review: the sense review harness and
  `review_batches` are on `main`, so phase 1 reuses them; `apply_form_drops` drops a lemma
  once every sense is dropped, so a bad word needs one row per concept link; this branch
  is 0.7.0 code while the measurements came from the 0.8.0 build, which only matters for
  phase 5 (the rebuild has to carry 0.8.0, so it waits for `feat/20_rare_words_topics` on
  `main`).
- 2026-11-15 : the user agreed phases 1 and 2 and asked to note the usage limit: 2% of the
  session (resets 17:29), 19% of the weekly all-models limit (resets Saturday 21:59) at the
  start; recorded in `02_pilot.md` so the pilot's share projects the full run.
- 2026-11-15 : phase 1 done: rulebook, harness, skill, tests (`make check` passes, 570);
  worklist of 4,814. Review: pre-1990 spellings moved from "valid" to `m`.
