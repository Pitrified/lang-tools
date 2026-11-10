---
status: planned
---

# Phase 7 - concepts for the closed-class words

## Overview

Give the closed-class words of the pt top 1,000 a card, through curated concepts (Q13): today
the build drops every WordNet sense of a listed word, and the hand corrections refuse to add
one. The drop stays, since those senses are wrong (*de* as the letter D, *o* as oxygen); only
the refusal is lifted, for a link to a curated concept.
Pronouns and quantifiers first, then articles, prepositions and conjunctions for completeness;
choosing which of them to drill is lang-tutor's job.
Context: [`00_start.md`](00_start.md) Q8, Q13; reuses phase 3
([`03_concepts.md`](03_concepts.md)); after phase 6, so the lemma ids are final.

## Plan

- The words: the 128 listed words in the pt top 1,000 (counted 2026-11-10, the 21 phase 2 added
  included), in groups:
  - personal pronouns (*eu*, *tu*, *você*, *ele*, *nós*, *me*, *te*, *lhe*, *mim*, *si*,
    *comigo*, *consigo*);
  - possessives (*meu*, *seu*, *nosso*, *teu* and their forms);
  - demonstratives (*este*, *esse*, *aquele*, *isto*, *isso*, *aquilo* and forms);
  - quantifiers and indefinites (*tudo*, *algo*, *ninguém*, *cada*, *qualquer*, *algum*,
    *ambos*, *tais*);
  - interrogatives and relatives (*quem*, *onde*, *qual*, *quais*, *quanto*, *que*);
  - articles (*o*, *a*, *os*, *as*, *uns*, *umas*);
  - prepositions (*de*, *em*, *para*, *pra*, *com*, *por*, *sobre*, *até*, *sem*, *entre*, *sob*,
    *após*, *desde*, *contra*, *durante*, *através*, *trás*);
  - conjunctions (*e*, *mas*, *ou*, *porque*, *quando*, *como*, *se*, *nem*, *pois*, *enquanto*,
    *embora*, *porém*, *entanto*, *apesar*);
  - contractions (*do*, *na*, *ao*, *pelo*, *num*, *dele*, *disso*, *neste*, ...).
- Concepts: one `concept_additions` row per meaning (personal pronoun "I", the definite article
  "the", the preposition "of, from"), with the lexfile of the nearest class, an English
  definition and the English members. A word with several meanings links to each and pins the
  commonest (*a* "the" over "to" and "her"; *que* "that" over "what", "than"). Masculine and
  feminine, singular and plural forms share their base word's concept with a form note
  (*minhas*: `feminine plural of "meu": my`); a contraction gets its first part's concept with a
  note (*do*: `contraction of "de" + "o": of the`). Expected about 70 concepts.
- Code: `add_sense` and the batch check in `sense_review` accept a closed-class word when the
  concept is a curated one (a key of `load_concept_additions`), and still refuse a WordNet
  concept. A test each, and the closed-class paragraph of `docs/library/lexicon.md` updated.
- Labels by subagents (Q6), one batch per group or two, proposing the concept rows and the
  links in the `02.1_apply_labels.py` format; I check every line. The concept rows go in first
  and are built, then the links are applied (`add` needs a built concept), then a second build.
- Gate, and every card of the 128 words read on 8010.

## Pitfalls

- The en members create en lemmas for *the*, *of*, *I*. Check that the en closed-class list
  does not drop them, and that they read well as translations.
- *um* and *uma* are not on the list ("one" is their WordNet sense): their article meaning
  "a, an" is added as a second sense here, with the number kept as the card or not, decided
  per word by the labels.
- A lemma the closed-class stage removes is created again by the sense addition; check that it
  keeps its frequency rank and part of speech.

## Out of scope

- Closed-class words beyond the top 1,000.
- Drill selection: lang-tutor decides which of these cards to show.

## Done when

- Every one of the 128 words has a card on a curated concept, or is listed with the reason,
  0 stale rows, `make check` and the gate pass, and each card was read.
