---
status: done
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

- Every tier-B pair has a reviewed row (6,701 / 6,701, done 2026-10-31).
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

## Tier B, third round (b0022 to b0034)

Thirteen batches (twelve of 200 pairs, one of 101), one subagent each, under guide
`debd21395107` (the word-form rule bounded by Q6). Tier B is complete: 6,701/6,701.

- **Results:** 88 full and 70 partial false friends, 624 cognates, 1,719 unrelated; 108 edge
  cases. Traps are 6% of the pairs, down from 9% in round 2.
- **Gold:** 61/65 (328/355 overall). Misses: *fundamentalismo* / *fundamentalist* and
  *estruturalismo* / it *strutturale* (b0033), *abusar* / it *abuso* (b0032), all gold `c` and
  agent `u` by the own-cognate clause; *lâmpada* / *lamp* (gold `p`, agent `c`).
- **Rule clash:** the Q6 clause "the known language's own cognate still wins" contradicts the
  guide's own `c` examples (*monarca* / it *monarchia*, *notar* / it *nota*) and the gold set.
  Reviewers split on it: b0024, b0026, b0028, b0031, b0032 and b0033 labelled word-form pairs
  `u` (*ideologia* / it *ideologo*, *semântica* / it *semantico*, *zoologia* / it *zoologo*),
  while b0022 and b0025 labelled them `c` (*pediatra* / it *pediatria*, *oncologia* / it
  *oncologo*). Raised as `00_start.md` Q7.

## Closing recheck (r0005 to r0010)

1,034 of the 1,035 mined keys re-checked in six batches under guide `8c251b3ed4b0` (the
word-form rule without the own-cognate clause, Q7); *relatório* / it *relatore* was skipped,
being a gold pair whose gold row is already `u`.

- **Changed:** 261 labels. 126 `u` to `c` (the round 3 word-form drift undone), 42 `f` to `u`,
  19 `u` to `f`, 14 `c` to `p`, 13 `p` to `u`, 12 `f` to `p`, 11 `c` to `u`, 10 `p` to `c`,
  8 `p` to `f`, 3 `u` to `p`, 2 `c` to `f`, 1 `f` to `c`. The Q5 verb / noun `c` rows mostly
  held: 11 went `u`.
- **Gold:** 23/30. The misses are meaning calls, not rule drift: *compromisso* / *compromise*,
  *pasta* / it *pasta*, *cantina* / it *cantina*, *palimpsesto* / it *palinsesto*, *logo* / it
  *logo*, *compositor* / *compositor*, *tenda* / it *tenda*.
- **Edge cases:** 85, 45 of them in `r0006`, the batch that held most of the old `!` rows.
- **Left for a later look:** the person-against-thing rule took *perfume* / *perfumer* and
  *depósito* / *depositor* to `f`; near-identical pairs against a moderately common known word
  still split between `f` and `u` (*lepra* / it *lepre* `f`, *balde* / *bald* `u`).

### Resume here

1. **Corpus rebuilt** on 2026-10-29 with the round 1 rows: 3,883 edges (3,262 cognate,
   280 partial, 341 full), 71 rare-word traps dropped, 6 stale, gate PASS. The seed gained four
   tier B edges.
2. **Rule questions settled** on 2026-10-29 ([`00_start.md`](00_start.md) Q1 to Q4): the
   word-form rule is in the rulebook, so round 2 runs under a new `prompt_sha`. The stale `c`
   rows it leaves behind are Q5.
3. **All rounds done; Q7 settled.** The closing recheck keys are in
   `data/work/lookalike_review/recheck_tier_b.txt`, 1,035 pairs, mined on 2026-10-31:
   - Q4: every tier B row flagged `!`, 324;
   - Q5: latest row `c` with one side a verb and the other a noun (part of speech from the
     corpus), any tier, 447;
   - Q6: *relatório* / it *relatore*, *microscópico* / it *microscopio*, 2;
   - Q7: latest row `u` under guide `debd21395107` whose two spellings, accents removed, share a
     prefix of 6 letters or more that covers all but at most 4 letters of the shorter one, 282.
   Re-checked as `r0005` to `r0010` (above).
4. **Final rebuild** on 2026-10-31: 5,523 edges (4,768 cognate, 356 partial, 399 full),
   237 rare-word traps dropped, 6 stale, gate PASS, seed unchanged. Phase closed; next is
   [`03_tier_depth.md`](03_tier_depth.md).
