---
status: in progress
priority: 0
description: |
  Agent review of the ~65k pt-en / pt-it look-alike candidates, in usefulness tiers A to E,
  against the rulebook. Reviewed rows land in data/curated/ and the corpus build turns them
  into look-alike edges (false friends and cognates).
comment: |
  Spun off from phase 11 of 09_concept_model on 2026-10-24. Phase 11 built the pipeline
  (gold set, generator, model, verifier, build input and gate, cards, lang-tutor surface);
  this folder only runs the review.
---

# Look-alike review

## Origin

Phase 11 of the concept model ([`11_false_friends.md`](../09_concept_model/11_false_friends.md))
built everything a look-alike edge needs, from candidate generation to the lang-tutor surface.
The paid verifier run was parked, and the candidates have been reviewed by agents since
2026-10-23, in batches spread over weeks.

On 2026-10-24 the user asked to spin "the tiers false friend efforts" off into a folder of their
own, "so that it can move independently from other development": all the context, the pointers
to the rules and batches, and the tracking of what is done and what is left. The plan text of
the review moved here from `11_false_friends.md` unchanged; phase 11 closed as done.

## Working set

Everything the review reads or writes, none of it under this folder:

- **Rulebook:** `docs/guides/lookalike_review.md`. Its hash is stored on every reviewed row as
  `prompt_sha`, so a change to it is deliberate and dates the rows after it.
- **One batch's workflow:** `.claude/skills/lookalike-review/SKILL.md`, which also covers
  orchestrating several batches and re-checks.
- **Tooling:** `lang_tools.lexicon.ingestion.lookalike_review` and its CLI,
  `python -m lang_tools.lexicon.ingestion.lookalike_review_cli` (`serve`, `apply`, `recheck`,
  `status`, `import-gold`).
- **Data**, all under Git LFS and committed with `git add -f`:
  - `data/curated/lookalike_worklist.jsonl`: the tiered worklist;
  - `data/curated/lookalikes.jsonl`: the reviewed rows, latest row per pair wins;
  - `data/curated/lookalike_review_log.jsonl`: per-batch numbers and gold agreement;
  - `data/curated/lookalike_gold.jsonl`: the 1000-pair gold set;
  - `data/work/lookalike_review/`: served batches, label files, the reservation lock and
    `recheck_keys.txt`.
- **Turning rows into edges:** `docs/guides/rebuild_corpus.md` (`build_initial`, about 3 to 4
  minutes, then the quality gate).
- **Cost per round:** [`00.1_usage_log.md`](00.1_usage_log.md), token use against the session
  and weekly limit meters.

## Approach

### Review through the agent harness (2026-10-23)

The user trusts the hand-labelled pairs more than a cheap model, and the Claude
subscription is a flat rate. So instead of a paid verifier run, the candidates are
reviewed by agents (this harness), in batches spread over weeks within the
subscription's limits. The OpenAI path stays available: the chain, prompts v1-v5, the
cached v6 draft and the 1000-pair experiment harness.

- **Order by usefulness** (`lookalike_review.build_worklist`, committed as
  `data/curated/lookalike_worklist.jsonl`):

  | Tier | Pairs | What |
  | --- | ---: | --- |
  | A | 5,499 | pt word very common (Zipf 4.5 or more) |
  | B | 6,701 | likely traps: near-identical or same-key pairs that the generator calls false friends, pt Zipf 2.5 or more, most common known word first |
  | C | 12,397 | the rest of pt Zipf 3.5 to 4.5 |
  | D | 17,490 | pt Zipf 2.5 to 3.5 |
  | E | 22,214 | the rare tail, last or never |

  Gold pairs stay out of the worklist and are imported directly (`import-gold`, tagged
  `manual`).
- **Batches.**
  - `serve` reserves 100 items under a lock and mixes in 5 hidden gold pairs.
  - The reviewer writes one compact line per item (`N c|p|f|u[!] [note]`).
  - `apply` validates the whole batch (every item, a note on every trap). It then appends
    to `data/curated/lookalikes.jsonl` (`unrelated` as rejected), tagged `agent-review`,
    with the batch id and the guide's hash, and logs the batch's numbers and gold
    agreement to `data/curated/lookalike_review_log.jsonl`.
  - Edges built from these rows carry the source `agent`.
- **Rules and context.**
  - `docs/guides/lookalike_review.md` is the rulebook: the four kinds, the hard cases (my
    calls from labelling the gold set), notes, edge cases and the label format.
  - The `.claude/skills/lookalike-review` skill is one batch's workflow.
  - One subagent per batch, so each starts from a small context. The orchestrating
    session only sees a four-line report per batch.
- **Edge cases.** `!` after the letter marks a judgement call (*fogo* / *fog*). It is
  applied as labelled and counted per batch, for a second look later.
- **Effort.** Labelling the 800 gold pairs inline grew the context by about 89k tokens,
  about 110 per pair. Most of the cost was re-reading a long conversation on every call,
  which subagents with fresh contexts avoid. The 1,000-pair calibration batch (10
  subagents) is the real measurement: the user reads the limit meter before and after.


## Decisions

- **Agents, not the paid verifier,** for now: the user trusts hand-labelled pairs more than a
  cheap model, and the subscription is a flat rate. The OpenAI chain, prompts v1-v5 and the
  experiment harness stay in phase 11 (`11_false_friends.md`, step 5, and the files under
  `../09_concept_model/11_false_friends/`), in case a cheap verifier comes back for the low tiers.
- **Most useful pairs first:** tiers A to E by pt frequency, with tier B the likely traps.
- **The rulebook moves forward, rows are not re-labelled wholesale.** A rule change applies from
  the next batch; older rows keep their `prompt_sha`, and a targeted `recheck` covers the labels
  the change can flip. The build keeps the latest row of each pair.
- **One subagent per batch, a lean orchestrator:** 200-pair batches, ids reserved up front, one
  commit at the end of a round.
- **The data stays where the code reads it.** This folder holds the record, not the data.

## Open questions

Raised by the reviewers in tier B round 1 (`02_tier_b.md`). Settling them changes the rulebook,
so they come before the next round, or the next round runs under the current guide and the
later rows carry the newer `prompt_sha`.

- Q1: A person noun against a thing noun of the same root (pt *fotógrafo* / en *photograph*)
  was labelled `f`. The guide counts "a person and the field" as a cognate.
  - a. `c`, extending "a person and the field" to a person and the thing they make.
  - b. `f`, since a learner reading *fotógrafo* as "photograph" is misled.
  - c. `p`.
  - Recommended: b, because the guide's test is whether the learner is misled, and the person
    / thing split is the misreading; state it next to the person-and-field example.
  - NEW_ANS:
- Q2: A verb against a noun of the same root (pt *albergar* / it *albergo*, pt *manifestar* /
  it *manifesto*) was labelled `c`. The guide already lists "a verb and its noun" as a cognate
  when the meaning carries over.
  - a. Keep `c`; add these two as examples of the existing rule.
  - b. `u` when the noun names a thing the verb does not (a hotel against "to shelter").
  - Recommended: a, because the rule exists and the agents applied it; the examples remove the
    doubt.
  - NEW_ANS:
- Q3: One pair was labelled twice in one batch with different marks (*cercar* / it *cercare*,
  `f` and `f!`). Either the batch served a duplicate or the reviewer repeated an item.
  - a. Check `serve` for duplicate keys in a batch and fix it there.
  - b. Accept it: the latest row wins, and the labels agree on the letter.
  - Recommended: a, because a duplicate wastes review and hides a serving bug; it is a quick
    check of the batch file.
  - NEW_ANS:
- Q4: Near-identical pairs against moderately common known words remain the main source of `!`
  (pt *lazer* / *laser*, *genro* / *genre*, *funda* / *fund*, *faca* / *fake*).
  - a. Leave them as `!` and decide in a later edge-case mining pass, as in tier A.
  - b. Set a Zipf band for the known word in the guide now (above 3.3, below some cut-off).
  - Recommended: a, because tier A's mining found its rules from about 250 flagged rows, and
    tier B has 130 so far.
  - NEW_ANS:
