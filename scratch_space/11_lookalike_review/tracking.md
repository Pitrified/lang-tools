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
| 2  | Tier B        | [`02_tier_b.md`](02_tier_b.md)               | in progress |
| 3  | Tier depth    | [`03_tier_depth.md`](03_tier_depth.md)       | draft       |
| 4  | Tiers C to E  | [`04_tiers_c_to_e.md`](04_tiers_c_to_e.md)   | draft       |
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
