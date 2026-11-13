---
status: in progress
---

# Phase 1 - pt from own-pt

## Overview

Build the pt backbone from upstream own-pt 1.0.0 (CC BY 4.0) instead of omw-pt 1.4 (CC BY-SA),
so no share-alike row is left when phase 2 writes the CC BY 4.0 notice.
Context: [`00_start.md`](00_start.md) Q1 and the own-pt probe.

## Goals

1. The build reads pt from `own-pt:1.0.0` through `wn`, taking its words and word-to-concept
   links, not its definitions or examples (some are Wikipedia text, CC BY-SA).
2. The cards for frequent pt words are as good as before, or the differences are known and
   accepted.
3. The curated rows that lose their pair are re-pointed or retired by new reviewed rows, never
   by hand edits to the corpus.

## Plan

- Map pt to `own-pt` in `sources/omw.py` (`OMW_LEXICONS` and the version per lexicon, since
  own-pt is `1.0.0`, not `1.4`); `acquire.download_omw` fetches it.
- Drop own-pt's definitions and examples at the adapter, with a test.
- own-pt carries relations of its own, which omw-pt 1.4 does not: 31,014 hypernym links,
  6,492 `similar`, part and member meronyms, and 517 pt sense antonyms. The reader opens each
  wordnet with no expansion and reads whatever relations it states.
  The first trial build showed own-pt 1.0.0 states hypernym and hyponym the wrong way round (its
  *canine* lists *dog* and *wolf* as hypernyms): against English's links each edge tied and was
  dropped, 36,122 of them. So own-pt's synset relations are not read (`NO_RELATION_LEXICONS`);
  English's edges connect the pt concepts through the ILI, as before. Its 517 sense antonyms
  (*aberto* / *fechado*, *leve* / *pesado*) have no direction and are kept.
- Check whether the spelling reform (`respell_pt`) still applies: own-pt may spell differently.
- Pin own-pt's version next to the OMW one: own-pt is `1.0.0`, the others `1.4`.
- Rebuild into a separate data folder first and compare with the current build on 500+ frequent
  pt words: card present, best sense, gloss, look-alikes. Deep probe: writes a second
  `lexicon/`, about the 140 s and 1.5 GB of the July rebuild; to be approved before it runs.
- Fix what the comparison finds through curated rows: the 8 best-sense pins and 191 look-alike
  words that lose their pair, the 53 sense additions that become moot; check the lost frequent
  words (*Brasil*, *sobre*, *há*, *qual*, *deve*, *enquanto*).
- Rebuild in place, regenerate the bootstrap seed, update `docs/library/lexicon.md` and
  `docs/guides/rebuild_corpus.md` where they name omw-pt.

## Out of scope

- fr, which stays out of the shipped dataset (Q2, Q8).
- The license files and card (phase 2).
- own-pt v1.1.0, which is not in the `wn` index.

## Done when

- The build's pt rows all come from own-pt, `_build.json` names it, and no own-pt definition or
  example is in the corpus.
- The 500+ word comparison is recorded here, with every regression fixed or accepted.
- `make check` and `make docs-build` pass.

## Trial build (2026-11-13)

Built into a scratch data folder (a copy of the raw cache plus own-pt, a copy of
`data/curated/`), `data/` untouched; 2:53 and 2.7 GB peak.
Code: pt maps to `own-pt:1.0.0` (`PINNED_VERSIONS`), read with no definitions or examples
(`NO_TEXT_LEXICONS`) and no synset relations (`NO_RELATION_LEXICONS`); `make check` passes.

`_build.json`, current build against the trial:

| | omw-pt | own-pt |
| --- | --- | --- |
| lemmas | 337,019 | 342,127 |
| senses | 541,400 | 577,345 |
| concept relations | 137,936 | 137,936 |
| sense relations | 3,992 | 4,268 (+276 pt antonyms) |
| inflected forms added / their senses | 12,395 / 49,675 | 12,950 / 73,366 |
| best-sense pins applied / stale | 724 / 0 | 721 / 3 |
| look-alikes applied / stale | 6,840 / 7 | 6,786 / 61 |
| sense additions: lemmas created / senses added | 455 / 659 | 430 / 611 |
| member-form drops applied | 341 | 245 |

Cards of the 3,000 most frequent pt words (wordfreq), each looked up as written and
capitalised, en gloss and translations:

- 1,366 unchanged; 1,160 with the same best sense but other senses changed; 304 with a
  different best sense; 15 lost; 30 gained. Senses on the shared cards: 11,834 to 15,332.
- **Lost** (15): mostly junk cards gone: *é* (the letter), *to* ("coat with tar"), *Q*, names
  read as English words (*Paulo*, *João*, *André*, *Antônio*, *Jack*, *Papa* as the poet,
  *luis*). Real losses: *quão*, *link*, *Palavras*.
- **Gained** (30): good: *Rio*, *Santos*, *Paris*, *poucas*, *pouca*, *estadual*, *carioca*,
  *Presidente*, *União*, the digits; junk: *vc* ("a speculator"), *silva* ("utter by
  whistling"), *v* (five), *L* (compass point), *at*.
- **Best sense changed** (304): the unpinned words take a new best sense from the senses own-pt
  adds. A read of the 60 most frequent, not an assessment: about 22 worse (*nova* a star, *zona*
  a to-do, *mesmo* really, *agora* right away, *sul* the US South, *coração* the seat of feelings,
  *armas* gun, *encontrar* see), 10 better (*empresa* company, *devido* due, *costa* coast,
  *viagem* journey, *seleção* team), about 28 equivalent. Pinned words keep their pin.
- The words the July probe flagged as lost from the wordnet (*Brasil*, *sobre*, *há*, *qual*,
  *deve*, *enquanto*) still have their cards or were never cards: none is in the lost list.
- The top-500 drill deck shares 370 words; the rest is mostly multi-word phrases moving around
  the frequency order.

The diff: `card_diff.tsv` in the session scratchpad (`p1_own/`), with the dump and compare
scripts.
