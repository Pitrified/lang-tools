---
status: done
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
  concept. The lexfile-to-part-of-speech map, duplicated in `concept_additions` and
  `sense_additions`, becomes one shared `LEXFILE_POS` that also knows the function-word
  classes (`pron`, `det`, `prep`, `conj`), so the new lemmas carry a part of speech lang-tutor
  can filter on. A test, and the closed-class paragraph of `docs/library/lexicon.md` updated.
- The inventory written by hand in one script (`07.1_closed_class_concepts.py`), not by
  subagents: 64 concepts that must agree with each other (one "that" for *esse*, another for
  *aquele*) are one design, not 128 independent labels, and writing them was cheaper than
  checking agent output line by line. The script checks every listed word has a link and
  every concept is used, and writes the label files for `02.1_apply_labels.py`. The concept rows go in first
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

## What the implementation found

- The plan review found the part-of-speech gap (a created lemma took its part of speech from
  a map of the four WordNet classes only, so every new card would have had none) and the
  duplicated map; both fixed in the code step above.
- *consigo* is mostly "I manage" (a form of *conseguir*), a WordNet concept, which a
  closed-class word may not take; it came off the list, as *devido* did, and links to both
  meanings with "I manage" as its card.
- 64 concepts and 142 links over 130 words: the 128 closed-class words of the top 1,000, and
  *um* / *uma*, which gain the article "a, an" as their card (the number "one" stays a sense).
  The links went in after a build with the concepts, the 10 pins of the main meaning of a
  multi-meaning word (*a* "the" over "to" and "her", *que* "that" over "what" and "than",
  *como* "how" over "as, like") after the next.
- Build: 66 concepts added (64 new), 71 en lemmas created (*the*, *of*, *nobody*), 659 senses
  and 455 lemmas from the sense additions, 724 pins, 0 stale. Look-alikes stale 11 to 8,
  as reviewed rows on words that exist again now apply; six accepted rows sit on the newly
  linked words (*qual* / it *quale*, *como* / *come*, *quando*, *durante* / *durata*), and the
  two on *pelos* (it *pelo* "hair", *peloso*) were reviewed for *pelos*
  "hairs", which this corpus spells *pêlos* (phase 6 kept *pêlo*), so they now sit on the
  contraction "by the". Left as they are; the *pêlo* / *pelo* homograph is the cause.
- All 130 cards read on 8010: each shows the chosen meaning and form note, 0 wrong. *um* and
  *uma* keep their old part of speech (noun, adverb), since their lemmas predate this phase;
  a client filtering on part of speech misses those two.
- `make check` 469 passed, docs build, gate PASS. The `docs/guides/sense_review.md` change
  (the refusal now names WordNet concepts) changes the rulebook hash future batches record.
