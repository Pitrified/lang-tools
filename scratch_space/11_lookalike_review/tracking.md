# look-alike review - implementation tracking

Agent review of the pt-en and pt-it look-alike candidates, tier by tier, against the rulebook
`docs/guides/lookalike_review.md`. Each batch appends reviewed rows to
`data/curated/lookalikes.jsonl`, and the corpus build turns them into look-alike edges. The
pipeline itself was built in phase 11 of the concept model
([`11_false_friends.md`](../09_concept_model/11_false_friends.md)). Origin, working set and
decisions in [`00_start.md`](00_start.md).

## Key decisions

- Agents review the candidates, for now, instead of the parked paid verifier.
- Tiers in order of usefulness: A (very common pt words), B (likely traps), then C to E by
  frequency, whose depth phase 3 decides.
- A rule change applies from the next batch; stale labels get a targeted `recheck`, and the
  latest row of a pair wins at build.
- 200-pair batches, one subagent each, a lean orchestrator and one commit per round.

## Phases

| #  | Phase         | Plan                                         | Status      |
| -- | ------------- | -------------------------------------------- | ----------- |
| 1  | Tier A        | [`01_tier_a.md`](01_tier_a.md)               | done        |
| 2  | Tier B        | [`02_tier_b.md`](02_tier_b.md)               | done        |
| 3  | Tier depth    | [`03_tier_depth.md`](03_tier_depth.md)       | done        |
| 4  | Tiers C to E  | [`04_tiers_c_to_e.md`](04_tiers_c_to_e.md)   | in progress |
| 5  | Close-out     | [`05_closeout.md`](05_closeout.md)           | draft       |

Status values: draft / planned / in progress / done / superseded / discarded.

## Log

Append-only. Newest at the bottom. The entries up to the spin-off are reconstructed on
2026-10-24 from the phase 11 plan, the usage log and the commit history.

- 2026-10-23 : batch review through the agent harness added (`lookalike_review`, the CLI, the
  skill, the rulebook) and the tiered worklist committed; the paid verifier run stays parked.
- 2026-10-23 : calibration, `a0001` to `a0010` (1,000 pairs, 100 per batch): gold 49/50; the
  1000-pair gold set imported as `manual` rows. Two rules adopted from `a0011`: grammatical
  words are `u`, and the known language's own cognate wins.
- 2026-10-23 : `a0011` and `a0012` at 200 pairs: about 420 tokens per pair against 720 at 100,
  so 200 became the batch size.
- 2026-10-23 : `a0013` to `a0028` in three rounds; the near-identical rule tightened from
  `a0021` (`f` only when plausibly confused), and three more rules settled from `a0029`
  (swapped letters, own cognate only when at least as close, partial versus full).
- 2026-10-23 : `a0029` to `a0033` finished tier A (5,499 / 5,499); rebuild with 2,946 edges.
- 2026-10-23 : staleness audit across the five guide versions; 532 stale labels re-checked as
  `r0001` to `r0003` (108 changed). Build bug fixed: a later `unrelated` row now retracts the
  earlier edge (latest row wins); rebuild with 2,882 edges.
- 2026-10-23 : edge-case mining over the `!` rows; two rules adopted (a rare known word never
  makes a trap, enforced at build under Zipf 3.3; inflected forms follow their base), and the
  conflicting families re-checked as `r0004`. Rebuild with 2,801 edges (2,462 cognate,
  177 partial, 162 full), 71 rare-word traps dropped, 6 stale.
- 2026-10-24 : tier B round 1, `b0001` to `b0012` (2,400 pairs, guide `6d74e34f`): 282 traps
  (12% of pairs), gold 54/60, 130 edge cases; four rule questions raised. The session limit
  was reached in the wrap-up, at 40 points or more against 30 planned.
- 2026-10-24 : spun off from phase 11 of `09_concept_model` into this folder on the user's
  request, so the review moves independently. The review sections of `11_false_friends.md`
  moved here unchanged (`01_tier_a.md`, `02_tier_b.md`, the harness design into
  `00_start.md`), and its usage log became `00.1_usage_log.md`; the open points were sorted
  into phases 3 to 5, and the tier B rule questions became `00_start.md` Q1 to Q4. Phase 11
  closed as done. Branch `feat/lookalike-review` renamed `feat/11_lookalike_review`. On main
  the same day: rebuild of the tier-A rows (2,801 edges, gate PASS) and the seed re-export.
- 2026-10-29 : tier B rule questions settled (`00_start.md` Q1 to Q4). The rulebook gains the
  word-form rule: a person against the thing they make is `f`, and a verb against a noun naming
  something else is `u`. The *cercar* double label was two different known words, not a
  serving bug. Q5 raised for the `c` rows the new rule makes stale.
- 2026-10-29 : Q5 answered: the stale verb / noun `c` rows are mined and re-checked at the end of
  tier B, in one `r` batch with the Q4 edge-case mining; added to `02_tier_b.md`.
- 2026-10-29 : rebuild with tier B round 1 on this branch: 3,883 edges (3,262 cognate,
  280 partial, 341 full; +1,082 against tier A, every round 1 `c`, `p` and `f`), 71 rare-word
  traps dropped, 6 stale, gate PASS; the seed re-export gained four edges.
- 2026-10-29 : tier B round 2, `b0013` to `b0021` (1,800 pairs, guide `bfa5d0c848d2`): 170 traps
  (9% of pairs), gold 43/45, 86 edge cases. Every batch applied on the first try. The new
  word-form rule produced one gold miss (*relatório* / it *relatore*); its scope is
  `00_start.md` Q6. Tier B at 4,200/6,701.
- 2026-10-29 : Q6 settled (a): the word-form rule applies only to close spellings and yields to
  the own-cognate rule; guide now `debd21395107`. Round 2 usage recorded in `00.1_usage_log.md`
  (27 session points, 3 weekly, about 69k tokens per agent).
- 2026-10-29 : rebuild with tier B round 2: 4,792 edges (4,034 cognate, 347 partial, 411 full),
  104 rare-word traps dropped, 6 stale, gate PASS; seed unchanged.
- 2026-10-31 : tier B round 3, `b0022` to `b0034` (2,501 pairs, guide `debd21395107`): 158 traps
  (6% of pairs), gold 61/65, 108 edge cases. Tier B complete, 6,701/6,701. The Q6 own-cognate
  clause clashed with the guide's `c` examples and the gold set, and reviewers split on it;
  raised as `00_start.md` Q7.
- 2026-10-31 : Q7 settled (a): the own-cognate clause dropped from the word-form rule, guide
  `8c251b3ed4b0`. Closing tier B recheck mined (1,035 keys: Q4 flags, Q5 verb / noun `c` rows,
  Q6 pairs, Q7 round 3 word-form `u` rows) and re-checked as `r0005` to `r0010`: 261 labels
  changed, 126 of them `u` to `c`; gold 23/30, 85 edge cases.
- 2026-10-31 : final tier B rebuild: 5,523 edges (4,768 cognate, 356 partial, 399 full),
  237 rare-word traps dropped (133 more than before: many tier B traps sit on known words
  under Zipf 3.3), 6 stale, gate PASS, seed unchanged, `make check` green. Phase 2 closed:
  every tier B pair reviewed and the closing recheck applied. Round 3 moved the weekly meter
  42% to 47%; its 5-hour reading was lost to the window reset.
- 2026-10-31 : phase 3 started. Plan review: `serve` takes a tier's most common words first, so
  the yield samples are drawn at random per tier and served through `recheck` instead.
- 2026-10-31 : phase 3 samples `c0001`, `d0001`, `e0001` applied (random 200 each, gold 14/15):
  kept traps 2.5% (C), 1% (D), 0 (E). Filtering a tier to known words of Zipf 3.3 or more loses
  no kept trap and cuts C by a third, D and E by half. Depth question raised as `00_start.md` Q8.
- 2026-10-31 : phase 3 samples extended to 1,000 random pairs per tier (`c0002` to `e0005`,
  gold 68/75): kept traps 3.2% (C), 1.2% (D), 0.7% (E), or 4.7%, 2.8%, 1.9% among the pairs a
  known-word filter keeps. Q8 updated with the new numbers; recommendation moved to C and D.
- 2026-10-31 : Q8 answered b: tiers C and D reviewed by agents, filtered to known words of Zipf
  3.3 or more; tier E stops. Phase 3 closed; phase 4 planned (filtered key lists served through
  `recheck`, C first).
- 2026-11-03 : two items from lang-tutor's `03_ui_followups` phase 1, which played the drills on the
  2026-10-31 corpus. The phase 3 samples (3,000 rows) had been committed after that build and
  were not in the corpus; rebuilt on the user's answer (lang-tutor Q10 a). The 139 terse trap
  notes get a re-check as `r0011` before the first C round (lang-tutor Q9 b), added to
  `04_tiers_c_to_e.md`.
- 2026-11-03 : rebuild with the phase 3 samples: 6,852 edges (6,046 cognate, 388 partial,
  418 full; +1,329), 257 rare-word traps dropped, 6 stale, gate PASS, seed unchanged.
- 2026-11-05 : one hand correction, from lang-tutor `03_ui_followups/00_start.md` Q12 (a):
  pt *era* / en *era* relabelled `partial` (a `manual` row, batch `correction`, the note of
  batch `a0001`), since `12_card_senses` pinned the *era* card to the noun "era" and a `full`
  label made en *era* its own pair-matching decoy. Recheck `r0001` had moved it to `full` on
  the frequent reading "was". Rebuilt, gate PASS.
- 2026-11-06 : phase 4 started, with the `r0011` step only (the user's scope; C and D wait).
  Plan review: the 168 terse trap notes are all hand-written gold rows off the worklist, which
  `recheck` cannot serve. Nothing served; raised as `00_start.md` Q9.
- 2026-11-06 : Q9 a: `recheck` serves curated pairs off the worklist (the gold pairs), with a
  test; `make check` green (422). `r0011` served the 168 terse gold traps (+5 hidden gold) to one
  agent: 85 full, 60 partial, 19 unrelated, 4 cognate; gold 5/5; 12 edge cases; every trap note
  now in the `pt "..."` form. 42 of the 168 hand labels changed kind: 14 full and 5 partial to
  unrelated (rare or distinct known words: pt *compositor* / en *compositor*, it *censo*,
  it *anello*), 12 full to partial (pt *realizar*, *balcão*, *colégio*, *pasta*), 7 partial to
  full (pt *testa* / it *testa*, *conto*, *maioridade*), 4 partial to cognate. The gold file
  that scores agreement still holds the old labels. Not yet rebuilt.
- 2026-11-06 : Q10 b: `_write_batch` leaves disputed gold pairs (latest row a review row of
  another kind) out of the hidden gold pool; 42 excluded on the real data; test extended,
  `make check` green (422).
