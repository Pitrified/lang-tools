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
- After the last round, one recheck pass ([`00_start.md`](00_start.md) Q4 and Q5): mine the
  tier B `!` rows for rules, as in tier A; mine the tier A and B `c` rows for a verb against a
  noun naming something else, which the word-form rule now makes `u`; add the round 2 rows the
  bounded rule changes (*relatório* / it *relatore*, *microscópico* / it *microscopio*, Q6) and
  any like them; re-check all of it as one `r` batch and rebuild.

## Done when

- Every tier-B pair has a reviewed row (2,400 / 6,701 so far).
- The recheck pass is applied.
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

## Tier B, second round (b0013 to b0021)

Nine 200-pair batches, one subagent each, under guide `bfa5d0c848d2` (the word-form rule).
Tier B stands at 4,200/6,701.

- **Results:** 87 full and 83 partial false friends, 772 cognates, 858 unrelated; 86 edge cases.
  Traps are 9% of the pairs against 12% in round 1, as the ordering moves to less common words.
- **Gold:** 43/45 (267/290 overall). Misses: *cava* / it *cava* (gold `c`, agent `p`, reading
  the pt armhole and ditch senses), *relatório* / it *relatore* (gold `u`, agent `f!`, applying
  the new person-against-thing rule to a pair whose spellings differ).
- **Points raised by the reviewers:**
  - the word-form rule against the own-cognate rule: *microscópico* / it *microscopio*,
    where it has *microscopico*, labelled `c` by the word-form rule;
  - the own-cognate rule when the cognate is the less close spelling: *reinar* / en *rein*
    (en *reign*), *cassino* / it *cassino* (it *casinò*), both `f!`;
  - identical spellings against a rare known word, `u!`: *castor* / en *castor*, *valentia* /
    it *valentia*.
  These went into `00_start.md` Q6, settled the same day: the word-form rule now needs close
  spellings and yields to the own-cognate rule.
- **Rebuild:** 4,792 edges (4,034 cognate, 347 partial, 411 full), 104 rare-word traps dropped
  (33 more than after round 1), 6 stale, gate PASS; the seed is unchanged.

### Resume here

1. **Corpus rebuilt** on 2026-10-29 with the round 1 rows: 3,883 edges (3,262 cognate,
   280 partial, 341 full), 71 rare-word traps dropped, 6 stale, gate PASS. The seed gained four
   tier B edges.
2. **Rule questions settled** on 2026-10-29 ([`00_start.md`](00_start.md) Q1 to Q4): the
   word-form rule is in the rulebook, so round 2 runs under a new `prompt_sha`. The stale `c`
   rows it leaves behind are Q5.
3. **Next round:** `b0022` onward, 2,501 tier B pairs left (13 batches, the last one 101 pairs). Reserve the ids up
   front (`serve --batch b0013 --size 200 --tier B`), launch one subagent per id with the skill,
   commit once at the end. Size it at about 3.3 session points per agent
   ([`00.1_usage_log.md`](00.1_usage_log.md), round 5): about 9 agents for 30 points.
