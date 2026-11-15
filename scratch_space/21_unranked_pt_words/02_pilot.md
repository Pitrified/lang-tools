---
status: in progress
---

# Phase 2 - Pilot of 500

## Plan

- Five batches of 100 by Claude subagents following the skill, a few at a time.
- Measured: the counts per label, the time per batch, the problems `apply` rejected, and
  the plan usage the pilot took. At the start (2026-11-15) the user's plan stood at 2% of
  the session limit (resets 17:29) and 19% of the weekly all-models limit (resets Saturday
  21:59); the user reads the usage after the pilot, and the full run is projected from the
  difference (about 8.6 pilots' worth) before it starts.
- Read by me: 100 labels across the batches, with the disagreements written down; the
  rulebook changed where they point to a rule, and the affected batches re-served.
- The numbers to the user before the rest.

## Done when

- 500 words labelled and applied; the user has the counts and the agreement.

## What the implementation found

- Five sonnet subagents, one batch of 100 each (u0001 to u0005), run in parallel; each took
  about 30 s and about 51k tokens. Every batch applied on the first try except u0002,
  refused once because an `m` spelling may not hold a hyphen.
- Counts over the 500: c 6, u 129, r 289, m 44, f 20, x 12. 76 words dropped (15%);
  of the kept ones 68% are rare, which with the stand-in of 1.5 puts them under acerta's
  floor of 2.0.
- My read of a random 100 (20 per batch): 5 disagreements, so 95% agreement:
  coccinela `f la` (a pt word, the ladybird; `r`), éolico `r` (misplaced accent: `m eólico`),
  encrustar `u` (`m incrustar`), breio `r` (the gloss is a bridle: `m freio`), vódca `u`
  (`m vodca`). A few buckets off by one (mecónio, framboeseira) not counted.
- My read of all 61 other drops: 2 wrong, túlipa and dendrite, both valid pt-PT spellings
  dropped as misspellings; and 2 compounds the hyphen rule forced to `x`
  (palavrascruzadas, folhadelata, which are `m palavras-cruzadas`, `m folha-de-lata`).
  Every other drop holds, including the glued phrases (tira de couro, carta de crédito).
- Rulebook and harness changes they point to, for the user to agree before the rest:
  allow a hyphen in an `m` spelling; a spelling a pt-PT dictionary lists is never `m`
  (túlipa, dendrite); a pt word that is also a Latin genus name is pt (coccinela),
  `f la` only for Latin forms (-idae, -aceae, binomials); a gloss naming a different
  common word points to `m` (breio -> freio). Then the 9 words above re-labelled.
- An `m` row records the correct spelling but the build only drops the misspelled
  lemma; when the correct word is missing from the corpus its meaning is lost with it.
  How many targets are missing is not measured yet.
- Usage: the user reads the plan usage after the pilot; the rest is about 43 batches,
  8.6 times the pilot's subagent work.
