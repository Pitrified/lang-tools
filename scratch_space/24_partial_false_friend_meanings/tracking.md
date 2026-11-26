# implementation tracking

A flag on each partial false friend whose look-alike mainly means a meaning the pt word shares
(it *tardi* "late" for pt *tarde*), from a review of the partial edges, carried on the card's
look-alikes so acerta can give no decoy from such a pair.
Analysis and decisions in [`00_start.md`](00_start.md).

## Key decisions

- A review, not a mechanical check: the concept-overlap test catches 38 of acerta's 104 shared
  decoys and flags 33 of its 170 good ones (`00_start.md`, "A mechanical check").
- The flag is a property of the pair, whichever language the look-alike's words are shown in.
- Every false-friend pair is reviewed, partial and full, 973 on `v0.11.0` (Q1); one curated log,
  `shared_meaning_log.jsonl`, sets `LookalikeHint.shares_meaning` (Q2), with a `w` label for a
  wrong main meaning that only lists it (Q3).
- 50 gold pairs, labelled by me and used as they are (Q4); Sonnet at high effort for every batch
  (Q5).
- What acerta does with the flag is acerta's; this folder ends at 0.12.0, tagged `v0.12.0` on the
  merge commit when the user merges (Q6).

## Phases

| #  | Phase                   | Plan                                           | Status |
| -- | ----------------------- | ---------------------------------------------- | ------ |
| 1  | The flag on the cards   | [`01_flag_on_cards.md`](01_flag_on_cards.md)   | done |
| 2  | Rulebook and harness    | [`02_harness.md`](02_harness.md)               | done |
| 3  | Pilot                   | [`03_pilot.md`](03_pilot.md)                   | done |
| 4  | The rest                | [`04_full_run.md`](04_full_run.md)             | done |
| 5  | Rebuild and release     | [`05_rebuild.md`](05_rebuild.md)               | done |

Status values: draft / planned / in progress / done / superseded / discarded.

## Log

Append-only. Newest at the bottom.

- 2026-11-26 : picked up on branch `feat/24_partial_false_friend_meanings` from `main`
  (`b523c13`). Measured read-only on the `v0.11.0` corpus: 503 partial edges (251 en, 252 it),
  448 with `means` in the other language; the concept-overlap test says shared for 156, and
  against acerta's 274 read partial decoys catches 38 of 104 shared and flags 33 of 170 good,
  so it is rejected for a review. Phases drafted; Q1 to Q6 raised.
- 2026-11-26 : Q1 to Q6 answered and folded in: all 973 full and partial pairs (Q1, c, not the
  recommended a), the flag as a field (Q2), the `w` label (Q3), 50 gold pairs used without a
  user read (Q4), Sonnet high for every batch (Q5, a without the Opus fallback: below 45 of 50
  the loop stops and asks), 0.12.0 with the `v0.12.0` tag (Q6). With full pairs in, the files
  are named `shared_meaning_*`, not `partial_meaning_*`. Phases planned.
- 2026-11-26 : phase 1 done (`969401f`). `ingestion/shared_meanings.py` (`SharedMeaningRow`,
  load, apply), `LookalikeRelation.shares_main_meaning`, codec column, build stage and manifest
  `shared_meanings`, `CACHE_VERSION` 12, `LookalikeHint.shares_meaning`; docs. Built by a Sonnet
  subagent (medium, an audit-trial variation); its label definitions were wrong in the docs and
  fixed by hand. `make check` 619 passed; `make docs-build` clean.
- 2026-11-26 : gold drafted for phase 2 (50 pairs: 30 partial, 20 full; 16 `s`, 31 `d`, 3 `w`).
  acerta's read is noisy for this question: it calls pt *lobo* / en *lobe* shared but pt *lobo* /
  it *lobo* good, and pt *bravo* / en *brave* good though pt *bravo* also means brave; so the
  gold is labelled from the pairs, and the agreement with acerta's read (phases 3 and 5) is a
  rough signal, not a score.
- 2026-11-26 : phase 2 done (`bbf68b7`). Rulebook `docs/guides/shared_meaning_review.md` and the
  50 gold pairs written by hand; `ingestion.shared_meaning_review` and its CLI, the
  `shared-meaning-review` skill and 9 tests by a Sonnet subagent at high effort, accepted with a
  docs reflow. `make check` 628 passed; `make docs-build` clean; worklist 973, gold first.
- 2026-11-26 : phase 3 done. Pilot `p0001`: 39 s, 58 d, 3 w, 15 edge cases; gold 49/50 (above
  the 45 bar, Q5); my read of the other 50 found none wrong. No rulebook change.
- 2026-11-26 : phase 4 done. `p0002` to `p0010` by nine Sonnet subagents: all 973 pairs labelled,
  293 s (269 partial, 24 full), 665 d, 15 w; my read of 100 found 2 wrong, re-checked with one
  more as `p9001` (all d). Gold still 49/50.
- 2026-11-26 : phase 5 done, folder done. Rebuilt: 293 pairs flagged, 0 stale, counts unchanged,
  gate PASS, seed and report restored. Against acerta's read: 84 of its 104 shared partial
  decoys flagged. 0.12.0 with its changelog; `v0.12.0` to tag on the merge commit. Left for
  later: the 15 `w` pairs' best senses, the 24 full pairs labelled `s`, the pt *bruto* note;
  acerta's re-export is its open point.
