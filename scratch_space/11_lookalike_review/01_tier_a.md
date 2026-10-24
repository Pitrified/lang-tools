---
status: done
---

# Phase 1 - tier A

## Overview

Review the 5,499 tier-A pairs (pt word at Zipf 4.5 or more), calibrate the batch size and the
cost, and settle the rulebook on what the batches show. Context: [`00_start.md`](00_start.md).

## Done when

- Every tier-A pair has a reviewed row (5,499 / 5,499 after `a0001` to `a0033`).
- Labels made stale by a rule change are re-checked under the current guide (`r0001` to `r0004`).
- The rebuilt corpus applies the rows and the gate passes.

All three hold: the 2026-10-24 rebuild gives 2,801 look-alike edges (71 rare-word traps
dropped, 6 stale rows), and every gate invariant passes.

## Record

The sections below moved here unchanged from `11_false_friends.md` on 2026-10-24.

**Calibration: the first 1,000 tier-A pairs (2026-10-23).** Ten subagents ran in
parallel, one 100-pair batch each (`a0001`-`a0010`):

- **Speed and size:** about one minute each, 4 to 5 tool calls, 70k to 73k tokens per
  subagent (about 720k in all). Most of that is fixed overhead: the system prompt, the
  skill and the guide. Batches of 200 would roughly halve the cost per pair.
- **Agreement:** 49 of 50 hidden gold pairs agreed. The one miss is *bloco* / *bloc*,
  gold cognate, reviewer partial; both are defensible.
- **Results:** 52 full and 27 partial false friends, 248 cognates and 673 unrelated, with
  51 edge cases. The gold set's 1000 pairs were imported as `manual` rows alongside.
- **Good finds:** *legal* (BR cool), *equipe* / *equip*, *empresa* / *empress*,
  *polícia* / *policy*, *maior* / *mayor*, *próprio* / *proper*, *fato* / *fate*,
  *dados* / it *dado*. Inflected forms are a real trap: *precisa* (needs), *era* (was),
  *fez* (did).
- **Rule questions the reviewers raised.** Tier A is full of function words, and the
  near-identical rule turns them into false friends a learner is never fooled by: *com*
  / *come*, *mas* / *mass*, *sem* / it *seme*, *para* / *par*, *tal* / *tall*.
  Reviewers also called pairs like *caso* / it *casa* false friends, although Italian has
  its own *caso*. Both refinements were adopted in the guide on 2026-10-23, from batch `a0011` on; the
  first 1,000 agent rows were not re-labelled:
  1. A grammatical word (preposition, conjunction, article, pronoun) is `u` unless its
     meaning has drifted from a shared root.
  2. When the known language has its own direct cognate of the pt word, a near-identical
     different known word does not mislead: `u`.
- **Corpus sense errors found on the way:** *seja* shows the unit "are", *cada* a
  Laotian coin, *dela* the pig genus. These are homograph senses leaking into function
  words, worth a later data-quality pass.

**Second calibration: two 200-pair batches under the refined rules (2026-10-23).** Two
subagents, `a0011` and `a0012`, 200 tier-A pairs plus 5 hidden gold each:

- **Cost:** 84k and 85k tokens, 6 tool calls, 80 to 100 seconds each. That is about 420
  tokens per pair against about 720 at 100 per batch: the fixed overhead (about 60k) now
  spreads over twice the pairs. The remaining 62.9k worklist items would take about 26M
  tokens at this size, about 315 subagents.
- **Agreement:** 10 of 10 gold pairs agreed (59 of 60 across all 12 batches).
- **Results:** 140 cognate, 245 unrelated, 12 full and 3 partial false friends, 14 edge
  cases. The false-friend rate dropped from 8% to 4% as the two rules turned look-alikes
  such as *ali* / *alike*, *carro* / it *caro* and *visto* / *vista* into `u`, and as the
  tier moves away from the most common words.
- **Worth a second look:** *amo* / it *amo* was labelled `f`, but both languages use *amo*
  for "I love", so it is at least `p`; *copa* / en *cope* is a near-identical `f` nobody
  would confuse.


## Near-identical rule tightened (2026-10-23, from `a0021` on)

Batches `a0013` to `a0020` (1,600 pairs) labelled short near-identical pairs against common known
words as `f!` (pt *dado* / en *dad*, *cabo* / *cab*, *belo* / *bell*), following the guide's old
wording, though nobody would confuse them. Two agents raised it independently. The guide now
asks for `f` only when a learner could plausibly read one word as the other; a short shared stem
nobody maps across is `u`. Earlier rows were not re-labelled; they carry `!` and the older
`prompt_sha`, so they are easy to find for a later pass.

## Three rules settled (2026-10-23, from `a0029` on)

Round 3 (a0021 to a0028) left three open questions, raised by agents or by gold misses. The guide
now answers them:

- **Swapped letters.** Two swapped neighbouring letters count as near-identical (pt *sopa* /
  en *soap*).
- **Own cognate versus a closer look-alike.** The known language's own cognate wins only when it
  is spelled at least as close to the pt word as the look-alike. pt *sopa* / en *soap* (gold
  `f`) and pt *branca* / it *branca* (agent `f!`) are `f`; pt *busto* / it *busta* stays `u`. A
  known word that only shares the spelling is not a cognate, so pt *seta* / it *setta* (gold
  `f`) is not blocked by it *seta* (silk).
- **Partial versus full.** A shared sense in ordinary use, even a secondary one, makes the pair
  `p` (pt *guardar* / it *guardare*, pt *brigar* / it *briga*, both gold `p`). Overlapping main
  meanings are `p`, not `c` (pt *andar* / it *andare*, gold `p`).

Under the new rules the gold row pt *busto* / it *busta* was wrong; it is relabelled from
`full` to `noise` (unrelated). Later, pt *torcer* / en *torque* was relabelled from `cognate`
to `noise` too. The gold pairs are also imported into `lookalikes.jsonl` as `manual` rows,
so relabelling the gold file alone leaves the corpus edge in place; both pairs got a newer
`manual` row (batch `gold-fix`, `unrelated`), and the rebuild has 2,880 edges. Rows from a0021 to a0028 were not
re-labelled; they carry the old `prompt_sha`.

## Staleness audit and targeted re-check (2026-10-23)

The guide changed four times during tier A. Each version is a distinct `prompt_sha`:

| Guide | Batches | Change | Which old labels it can flip |
| --- | --- | --- | --- |
| `1d1b6f20` | a0001-a0010 | first rules | - |
| `c8229b98` | a0011-a0012 | grammatical words are `u`; own cognate wins | `f`/`p` to `u` |
| `fdec6154` | a0013-a0020 | inflected forms count by their most frequent reading | `f`/`p` either way |
| `1ae8850c` | a0021-a0028 | near-identical is `f` only when plausibly confused | `f` to `u` |
| `0b36ffd0` | a0029-a0033 | swapped letters; own cognate only when at least as close; shared ordinary sense is `p`, overlap is `p` not `c` | `u` to `f`, `f` to `p`, `c` to `p` |

Most changes only move traps (`f`/`p`) to something else, so a full pass is not needed. The
stale candidates, written to `data/work/lookalike_review/recheck_keys.txt`, are:

- all 269 `f`/`p` rows from a0001 to a0028;
- 260 `u` rows whose two words are near-identical under the current definition (accent,
  doubled letter, final vowel, swapped letters), where the old own-cognate rule could have
  hidden a closer look-alike;
- 3 cognate rows that differ by swapped letters.

Not covered: `c` rows that the overlap rule would make `p` (pt *andar* / it *andare*). Those
cannot be found by spelling, and a missed `p` costs less than a wrong trap. A spot check in
lang-tutor found the problem: the most frequent trap cards were *para* / *par*, *mas* /
*mass*, *com* / *come*, all from a0001 under the first rules.

The 532 pairs were served as re-check batches `r0001` to `r0003` with the new `recheck`
command; the corpus build keeps the later row of a pair.

**Result.** Gold 13/15. 108 of 532 labels changed (20%): 65 `f` and 11 `p` became `u` (all
the grammatical-word traps, *para*, *mas*, *com*, *sem*, *ser*, among them), 12 `f` became
`p`, 6 `p` became `f`, 10 `u` became `f`. The build had a bug: a later `unrelated` row was
filtered out as rejected and never retracted the earlier edge, so the first rebuild showed
2,958 edges. `load_lookalikes` now keeps only the latest row of each pair. The rebuild gives
2,882 edges (2,471 cognate, 206 partial, 205 full). The lang-tutor spot check now leads with
real traps: *precisa*, *cara* / it *caro*, *empresa* / *empress*, *era*, *time* (BR team),
*sete* / it *sete*, *saber* / en *saber*. The re-check batches flagged many edge cases (58 in
532), mostly short near-identical pairs against moderately common known words.


## Open points after tier A (2026-10-23)

Besides tiers B to E, in priority order:

1. **Function-word translations.** Done 2026-10-23: `ingestion.closed_class` drops every
   sense of a pt/es/fr/it closed-class word (231 senses, 118 lemmas). Six cognate edges
   went stale with their lemmas (*quando* / it *quando*, *qual* / it *quale*, ...).
   Still open: inflected verb forms with a junk best sense (*é* "e", *são* "healthy",
   *seja* "are", the unit), and *brasil* "brazilwood". Original note: Rare homograph senses win the best-sense pick for very
   common words, so lang-tutor shows *para* as "for example", *com* as "aft", *como* as
   "east" (also *seja* "are", *cada* a Laotian coin, *dela* the pig genus). A learner meets
   these on the first cards. Fix: a curated override for the top function words, or a rule
   that a sense with no frequency data cannot become the best sense of a common lemma.
2. **Merge `feat/lexicon` into main.** lang-tutor pins `lang-tools@main`.
3. **Re-export the sample seed** (`data/bootstrap/`); its 8 look-alike edges predate the
   review, so tests and the webapp sample mode run on stale traps.
4. **Mine the `!` edge cases** (about 250) and the open gold disagreements (*fausto*,
   *salá*, *preservar* / *preserver*, *macaco*, *estufa*, *pagode*) for the next rule.
5. **Decide the tier depth.** Measure the false-friend yield on 200-pair samples of C, D, E
   before paying for them (about 75 weekly points for B to E); or bring back a cheap-model
   verifier for the low tiers, with agents checking only its traps.
6. **End-to-end check in lang-tutor:** the HTTP read service on the rebuilt corpus, the trap
   note after a wrong tap, and whether the trap bonus over-selects now that traps lead the
   frequent cards.
7. **Housekeeping:**
   - (a) read the cache-probe result into `11_false_friends/prompt_caching.md`;
   - (b) add `cache_write_tokens` to `Usage`;
   - (c) close or fold the parked verifier (#22) and cheap-model prompting (#26) into item 5;
   - (d) overlap cognates (*andar* / *andare*) the re-check could not find by spelling.

Where these went on 2026-10-24:

- 1: the closed-class drop is done; the leftover (junk best senses on inflected verb forms,
  *brasil*) is corpus quality, kept in the concept-model backlog.
- 2, 3 and 4: done (the seed re-export landed on main on 2026-10-24; the edge-case mining is
  below).
- 5 and 7 (a) to (c): [`03_tier_depth.md`](03_tier_depth.md).
- 6 and 7 (d): [`05_closeout.md`](05_closeout.md).

## Edge-case mining (2026-10-23)

After the re-check, 113 rows still carry `!` as their latest label. Grouped by spelling
(identical, near-identical, shared root, other) and kind, two patterns cover most of them,
and the open gold disagreements fit the same two:

1. **A rare known word.** Identical or near-identical pairs whose known word a learner
   probably does not know: en *palaver* (Zipf 2.2), *bonito* (2.5), *tardy*, *cede*, *primo*,
   *quart*, *pinto*, *cantor*, *saber*, *valor* (3.2), it *bastante*, *lindo*, *podere*. The
   agents split them between `f` and `u`, because the guide calls a near-identical pair `u`
   when the known word is rare but treats identical spelling as `f` or `p` whatever the
   frequency. Gold *fausto* / it *fausto* and *salá* / it *sala* are the same question. The
   confusable ones sit well above: *cost* 5.2, *door* 5.1, *floor* 4.9, *come* 5.8. Of the
   242 current traps, 46 have a known word under Zipf 3.3.
   *Candidate rule:* a known word under Zipf 3.3 never makes a trap (`u`), identical
   spelling included. Being mechanical, it could also be a build filter on trap edges
   (the generator keeps candidates down to Zipf 2.0) instead of a reviewer judgement.
2. **Inflected forms of one word disagree.** The same known word gets different labels
   against forms of one pt word: *empresa* `f` / *empresas* `u` (*empress*), *bonito* `f`
   / *bonita* `u`, *branco* `f` / *branca* `u`, *quarto* `f` / *quarta* `u`, *cantor* `p`
   / *cantora* `u`, *fundo* `p` / *fundos* `c`. 16 such families exist; the rest differ
   for a reason (*costas* is "back", *privada* "toilet", *secretaria* "office",
   *escritório* "office"). Gold *preservar* / *preserver* is the derived-form variant.
   *Candidate rule:* a plural or feminine form takes the label of its base form unless it
   has an everyday meaning of its own, which the note then names.

**Both rules adopted (2026-10-23).** The guide states them, and the build enforces the
first: `drop_rare_traps` removes any `full` / `partial` row whose known word is under Zipf
3.3 (`MIN_TRAP_KNOWN_ZIPF`); the manifest counts it under `lookalikes.rare_traps_dropped`.
The 34 rows of the 16 conflicting families were re-checked as `r0004` (gold 4/5): *empresa*
and *empresas* are now both `f` against *empress*; *bonito*/*bonita*, *quarto*/*quarta*,
*cantor*/*cantora* against their rare en words are `u`; *costas* and *secretaria* keep a
label of their own. The rebuild has 2,801 edges (2,462 cognate, 177 partial, 162 full),
71 rare-word traps dropped, 6 stale.

Smaller patterns, no rule proposed: shared-root pairs across parts of speech (*propaganda*
/ it *propagandare*, *trânsito* / it *transitare*, *negócio* / it *negoziare*), labelled `c`
or `p` inconsistently but rarely misleading; and register-dependent BR/PT words
(*equipa*, *legal*, *vila*).
