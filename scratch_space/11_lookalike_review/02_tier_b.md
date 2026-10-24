---
status: in progress
---

# Phase 2 - tier B

## Overview

Review the 6,701 tier-B pairs: near-identical or same-key pairs that the generator calls false
friends, pt Zipf 2.5 or more, most common known word first. This is where the traps are, so it
comes before the frequency tiers C to E. Context: [`00_start.md`](00_start.md), depends on
[`01_tier_a.md`](01_tier_a.md).

## Plan

- Settle the rule questions of round 1 ([`00_start.md`](00_start.md) Q1 to Q4) in the
  rulebook, or run the next round under the current guide.
- Rounds of 200-pair batches, ids reserved up front, one subagent per id, one commit per round.
- Rebuild the corpus after each round and note the edge counts here. The
   tier B rows exist only on this folder's branch, so the rebuild runs here.

## Done when

- Every tier-B pair has a reviewed row (2,400 / 6,701 so far).
- The rebuilt corpus applies them and the gate passes.

## Record

## Tier B, first round (b0001 to b0012)

Twelve 200-pair batches, one subagent each, under guide `6d74e34f`. Tier B stands at 2,400/6,701.

- **Results:** 179 full and 103 partial false friends, 800 cognates, 1,318 unrelated; 130 edge
  cases. Traps are 12% of the pairs against 4% in late tier A, as the tier's ordering intends.
- **Gold:** 54/60 (224/245 overall). Misses: *rato* / it *rata* (gold `f`, agent `u` because
  it *ratto* is as close), *bisel* / *bezel* (gold `c`, agent took *bezel* as rare), *forca* /
  it *forca* (gold `p`; the pt senses mix *força* and *forca*), *conto* / it *conto* (gold `p`,
  agent `f`), *sair* / it *salire* (gold `f`, agent `u`), *pupila* / *pupil* (gold `p`, agent
  `c`).
- **Rule questions raised:**
  - a person noun against a thing noun (*fotógrafo* / *photograph*, labelled `f`);
  - a verb against a noun of the same root (*albergar* / it *albergo*, *manifestar* / it
    *manifesto*, labelled `c`);
  - one pair labelled twice in a batch with different marks (*cercar* / it *cercare*, `f` and
    `f!`);
  - near-identical pairs against moderately common known words stay the main source of `!`
    (*lazer* / *laser*, *genro* / *genre*, *funda* / *fund*, *faca* / *fake*).

### Resume here

1. **Rebuild the corpus** so the 2,400 tier B rows become edges (`docs/guides/rebuild_corpus.md`,
   no agents, about 4 minutes), and note the edge counts here. The
   tier B rows exist only on this folder's branch, so the rebuild runs here.
2. **Settle the rule questions above** ([`00_start.md`](00_start.md) Q1 to Q4) in
   `docs/guides/lookalike_review.md` before more batches, or
   accept that later rows carry a newer `prompt_sha`.
3. **Next round:** `b0013` onward, 4,301 tier B pairs left (about 22 batches). Reserve the ids up
   front (`serve --batch b0013 --size 200 --tier B`), launch one subagent per id with the skill,
   commit once at the end. Size it at about 3.3 session points per agent
   ([`00.1_usage_log.md`](00.1_usage_log.md), round 5): about 9 agents for 30 points.
