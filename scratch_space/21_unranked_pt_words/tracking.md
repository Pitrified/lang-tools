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
| 2  | Pilot of 500           | [`02_pilot.md`](02_pilot.md)             | done |
| 3  | The rest               | [`03_full_run.md`](03_full_run.md)       | done |
| 4  | Buckets in the build   | [`04_build.md`](04_build.md)             | done |
| 5  | Rebuild and release    | [`05_rebuild.md`](05_rebuild.md)         | done |

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
- 2026-11-15 : phase 2, the pilot: 500 words in five parallel batches; c 6, u 129, r 289,
  m 44, f 20, x 12. My read of a random 100: 95% agreement; of the 61 other drops 2 wrong
  (túlipa, dendrite) and 2 compounds lost to the no-hyphen rule. Four rulebook and harness
  changes proposed in `02_pilot.md`; waiting on the user and the usage reading.
- 2026-11-15 : the user agreed the fixes and the rest, reading the usage after the pilot at
  17% of the session and 21% of the week (from 2% and 19%), so the rest runs in waves of 10
  batches with a reading between waves. Harness: hyphenated `m` spellings, `recheck`
  batches whose new label restores a dropped word or retracts a bucket (tests seen failing
  without the restore); rulebook: pt-PT spellings, Latin genus names, gloss mismatches,
  glued compounds (`25119ae`). The 9 pilot words re-labelled (`73be436`). Wave 1, u0006 to
  u0015 in parallel, about 30 s and 52k tokens each (`0f4f494`): 1,500 of 4,814 labelled,
  c 11, u 366, r 878, m 145, f 58, x 42. For a later re-check from the reports: íngrime
  (`m íngreme`), gordurenta (real, not `x`), tunesino (`m tunisino`), relojeiro
  (`m relojoeiro`), rádon (valid pt-PT, not `m`), butâni (`m butanês`).
- 2026-11-15 : waves 2 to 4 (u0016 to u0049) applied; every worklist word labelled. My
  read of 100 across the waves: 95% agreement. Re-check `r0002` fixed those 5 and 12
  flagged labels. Final: 4,045 kept (c 43, u 1,218, r 2,784), 769 dropped (m 423, f 227,
  x 119). Phases 2 and 3 done; phases 4 (buckets in the build) and 5 (rebuild, after
  `feat/20_rare_words_topics` reaches `main`) wait for the user.
- 2026-11-15 : phase 4 done: `with_bucket_zipf` overlays the bucket stand-ins on the
  frequency table before `enrich`, no change to the score; manifest counts; tests (`make
  check` passes, 575). Phase 5, the rebuild, waits for `feat/20_rare_words_topics` on
  `main` and the user's go.
- 2026-11-15 : the user had me merge `feat/20_rare_words_topics` into `main` locally
  (`780788a`, nothing pushed); this branch rebased onto it, with one conflict in the build
  manifest and its test (both branches added keys; both kept). `make check` passes, 584.
  The two open points this folder came from are removed from `open_points.md`; the
  stray words that do have a frequency stay deferred as `00_start.md` Q2 says.
- 2026-11-15 : phase 5 done: rebuilt with the review (769 pt words dropped, 4,045 stand-ins,
  pt no-frequency words 8,597 to 3,783, all multiword); seed unchanged; `make check` 584;
  the quality gate's one known row; 0.9.0 and its changelog. Folder done.
