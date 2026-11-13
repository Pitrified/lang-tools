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

## Why the best senses changed (2026-11-13)

Read-only, on the two trial dumps and the Parquet. For a pt word every sense ties on
`sense_frequency` (the SemCor split is English-only), so the card's best sense is the concept
with the highest `commonness`, an English-derived count. Classified by whether the old best
sense is still on the word and whether the new best is a sense own-pt added:

| | count | examples |
| --- | --- | --- |
| old sense kept, an own-pt sense outranks it | 125 | *mesmo* truly, *agora* immediately, *sul* the US South, *zona* disturbance, *empresa* company |
| the same, on an inflected form (copies its base's senses) | 77 | *armas* gun, *problemas*, *jovens*, *perdeu*, *voltou* |
| old sense gone, another existing sense takes over | 58 | *nova* the star, *brasileira*, *empresas*, *santa*, *notícias*, *escolas*, *costa*, *viagem* |
| old sense gone, an own-pt sense takes over | 28 | *todo*, *tão*, *devido*, *velha*, *curta*, *valores* |
| the two above, on inflected forms | 16 | *pessoas*, *humana*, *vermelha*, *estranha* |

Two causes:

1. **More senses, ranked by English commonness** (202). own-pt gives frequent words more senses,
   many of them real Brazilian ones (*zona* "a mess"), and the commonness tie-break prefers
   whichever concept is common in English. The ranking is unchanged; it has more to choose from.
   Inflected forms inherit it from their base, and a pin on the base fixes the form too
   (`propagate_base_pins`).
2. **Feminine and plural words lost their adjective or noun sense** (about 70 of the 102 "old
   sense gone"). own-pt lists adjectives in the masculine and nouns in the singular more strictly
   than omw-pt, which had *nova*, *brasileira*, *empresas* as members of the adjective and noun
   synsets. In own-pt such a word exists only through another sense (*nova* the star), and
   `apply_inflections` skips every word the build already has (`known`), so *nova* never gets
   "feminine singular of *novo*". The rest of the 102 are singular words whose omw-pt pair own-pt
   does not have (*costa*, *viagem*, *depois*).

## The forms fix (2026-11-13, `00_start.md` Q10)

`apply_inflections` now gives a word the build already has the base senses of a noun or
adjective reading whose class the word has no sense of (*nova*, only the star in own-pt, gains
"feminine of *novo*"). Verb readings of existing words and words with a reviewed row are left
alone, and `propagate_base_pins` skips a form with its own pin.

A first version extended any existing word that lacked the base's concepts (656 words) and
regressed feminine person nouns (*irmã* to "a male with the same parents", *tia*, *garota*) and
plurals that already had their noun (*leis*, *livros*). The class rule extends 242 words.
Against the first trial build it fixes 7 cards (*brasileira*, *santa*, *velha*, *francesa*,
*louca*, *altos*, *antigos*) and *nova* now means "new"; it moves 10 feminine nouns to the
adjective (*física*, *lógica*, *prática*, *seca*, *escrita*, *partida*, *negra*, *muita*,
*pobres*, *produtores*). The added senses are right; the commonness ranking puts them first,
which is the Q11 review's job. Totals: 577,820 senses, 73,841 of them inflection senses.

## Review (`00_start.md` Q11)

The review set: the pt words among the 3,000 most frequent whose best sense differs from the
omw-pt build (307 in the fourth trial), served as re-check batches by `sense_review_cli recheck`
on the corpus rebuilt in place, labelled per `docs/guides/sense_review.md`.

Done on 2026-11-13, on the corpus rebuilt in place with own-pt (the omw-pt corpus is kept in the
session scratchpad):

- **`m0008`**: the 90 served words of the 1,000-card worklist (plus 2 gold): 39 pins, 2 wrong
  links dropped, 6 additions (*planos* "plans", *notícias* "news", *campos* "fields", *bonita*
  "pretty", Brazilian *quinta* Thursday and *quarta* Wednesday), 3 edge cases. Gold 1/2: the miss
  is *um*, kept as the article against the rule "pin one"; gold rows are not applied, so *um* was
  pinned to "one" by hand (`sense_review_cli pin`).
- **The worklist** was regenerated at 3,000 cards from the own-pt corpus and the removed lemmas
  appended (3,040 rows). 178 words of the old worklist left it: they are inflected forms now,
  which the worklist leaves out (a form follows its base's pin); their rows still apply, since
  the build does not read the worklist.
- **`m0009`**: the 107 changed words between rank 1,000 and 3,000 (plus 2 gold): 34 pins, 16
  additions (mostly plurals own-pt links to one narrow sense: *produtos* "a mathematical
  product", *linhas* "a short letter", *efeitos* "influence"), 3 dropped links, 2 words removed
  (*vc*, *at*), 8 edge cases. Gold 2/2.

Rebuilt in place: 916 pins applied, 1 stale; forms inherit 773 pins from their base (441
before). Of the 247 cards among the 3,000 most frequent words whose best sense still differs
from the omw-pt build: 141 reviewed under the current rules, 43 forms of a reviewed base, 4
capitalised words or digits, and 59 unreviewed: 31 words outside the 3,000-card worklist
(mostly verbs ranked low by their card's sense frequency: *cair*, *ligar*, *permitir*,
*realizar*) and 28 forms of such a base (*permite*, *lançou*, *caiu*).

Then, on the same day:

- **The worklist** was regenerated at 7,800 cards (the 31 verbs sit up to rank 7,757 by their
  card's sense frequency; the 5,000 first estimated was wrong) plus the removed lemmas.
- **`m0010`**: those words that are cards (42, plus 2 gold): 19 pins, 1 addition (*envolver*
  "involve"), 2 edge cases; gold 2/2.
- **Rule-made forms that are no forms.** own-pt lacks lowercase *paris*, *castro* and *acerca*,
  which omw-pt had as words, so the rules made them forms of *parir*, *castrar* and *acercar*.
  Reviewed drops ran before the inflection stage and could not reach them, so the build now runs
  the drops a second time after it, on rule-made senses only (a reviewed addition still wins);
  the three are dropped with `sense_review_cli drop`.

Rebuilt in place: 958 pins applied, 1 stale; forms inherit 1,075 pins from their base. Of the
233 cards among the 3,000 most frequent pt words whose best sense differs from the omw-pt build,
165 are reviewed, 63 are forms of a reviewed base, 4 are capitalised words or digits, and 1
(*s*, the symbol) is left as it is.
