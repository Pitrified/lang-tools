---
status: planned
priority: 0
description: |
  Give pt its number words and modal verbs. Half the cardinals (*cinco*, *doze*, *trinta*) and
  every form of *poder* "can" and *dever* "must" (*pode*, *deve*, *possa*) have no lemma, and
  WordNet holds no concept for a modal verb, so no review could link them.
comment: |
  Raised in scratch_space/13_missing_senses (03_recount.md, "Cards still wrong"; tracking.md
  2026-11-06), whose review served only lemmas the corpus already had.
---

# pt number words and modal verbs

## The idea

The `13_missing_senses` review fixed the senses of the pt top 1,000 cards, but a card needs a
lemma, and some of the most frequent pt words have none.
Two groups were named there: the number words (*doze*, *quinze*, *trinta*), and the modal verbs
(*deve*, *possa*), which WordNet does not model at all.
This folder adds both.

## Current state (2026-11-08, corpus of v0.4.0)

Measured on the built corpus against `wordfreq` pt.

### Number words

Of 43 cardinals checked, 20 have no lemma:
*uma* (zipf 7.0), *cinco* (5.4), *nove* (4.8), *doze* (4.3), *quinze* (4.2), *trinta* (4.5),
*quarenta* (4.2), *cinquenta* (4.1), *sessenta* (4.0), *setenta* (3.9), *cento* (4.5),
*milhões* (5.4), the teens *catorze* / *quatorze*, *dezesseis* / *dezasseis*, *dezessete*,
*dezoito*, *dezenove* / *dezanove* (pt-BR and pt-PT spellings).
Present: *um*, *dois*, *duas*, *três*, *quatro*, *seis*, *sete*, *oito*, *dez*, *onze*,
*treze*, *dezassete*, *vinte*, *oitenta*, *noventa*, *cem*, *duzentos*, *trezentos*,
*quinhentos*, *mil*, *milhão*, *bilhão*.

The English concepts all exist, each as a pair of WordNet twins: an adjective "denoting a
quantity consisting of 12 items" (`bd61c40ed942`) and a noun "the cardinal number that is the
sum of eleven and one" (`ed663a6fa537`).
The present pt numbers are linked inconsistently: *dez*, *vinte*, *cem*, *duas* to the noun,
*seis* to the adjective (plus "six-spot", the playing card), *mil* to both.
The ordinals are present (*primeiro* to *décimo*), except *segunda*.

No code is needed: a `sense_additions.jsonl` row creates a missing lemma and links it.

### Modal verbs

*poder* exists only as the noun "power", and *dever* as the noun "duty" plus the verb "owe".
Their modal meanings, "can, be able to, may" and "must, have to, should", are in no concept:
WordNet has no modal verbs, and en *can*, *must*, *may* are only "tin can", "grape must",
the month.
The nearest concept, the adjective "able" ("usually followed by 'to'"), is a near miss under
the rulebook, not the card.

None of their frequent forms has a lemma (zipf in brackets):
*pode* (6.2), *podem* (5.7), *poderia* (5.3), *possa* (5.0), *podia* (5.0), *poderá* (4.8),
*podemos*, *puder*, *posso*, *pude*, *pôde*, *poderão*, *podiam*, *pudessem*, *pudesse*;
*deve* (5.7), *deveria* (5.2), *devem* (5.2), *devia* (4.8), *devemos* (4.7), *devo* (4.6),
*deverá*, *deviam*.
About 30 forms above zipf 4.

So the modals need concepts of their own: a curated concept, which the corpus has no input for
yet (every concept comes from OMW, keyed by its synset).

### The wider gap

Numbers and modals are a slice of a larger gap: 366 of the pt top 1,000 `wordfreq` words have
no lemma.
Most are closed-class words WordNet does not model (*de*, *que*, *o*, *eu*, *você*, *isso*),
verb forms (*tem*, *vai*, *está*, *foi*), plurals (*anos*, *amigos*), names (*paulo*,
*brasil*) and English (*the*, *twitter*).
That is a design question of its own (Q1).

## Proposed approach

1. Assess the wider gap (Q1): classify the absent words of the pt top 1,000, and measure the
   top 2,000 and 5,000. A first count: 730 of the top 2,000 absent (37%), 2,222 of the top
   5,000 (45%). The 2,001 to 5,000 band is mostly inflected forms (*conseguem*, *dizia*,
   *poucas*, *decisões*), which points at an inflection question rather than per-word rows.
2. Numbers: add the 20 missing words, labelled by subagents and applied with `add` (Q6), on the twin chosen in Q4, with a
   form note where the word is a form (*uma* the feminine of *um*, *milhões* the plural of
   *milhão*), and bring the present numbers onto the same twin.
3. Curated concepts: a new curated input that creates a concept the sources lack, keyed on a
   stable manual source key, with an English gloss and English members, applied at build before
   the sense additions so an addition can link to it (Q2).
4. Modal verbs: the concepts from Q3, *poder* and *dever* linked to them and pinned, their forms
   added with form notes (Q5).
5. Release v0.5.0 and bump lang-tutor's pin.

Steps 2 to 4 each end with a rebuild and the gate, as in `13_missing_senses`.

## Open questions

- Q1: Scope. The 366 absent words include these two groups, but most of the rest are function
  words and pronouns, which have no WordNet concept either and would need the curated concepts
  of Q2 on a much larger scale, with their own rules (what is the card for *de*?).
  - a. Numbers and modals only. Spin the wider gap off as a draft folder, which can reuse
    Q2's curated concepts.
  - b. Widen this folder to the 366.
  - Recommended: a, because the two groups are closed lists that can be checked by hand, while
    the wider gap needs rules for closed-class words that do not exist yet.
  - ANS: a for now (user, 2026-11-09), but not a new folder: the wider gap may become a later
    phase of this one. Its scope is assessed first, including how far the gap reaches past
    the top 1,000 (top 2,000 and 5,000). Phase 1 does that.
- Q2: How a modal gets a concept.
  - a. A curated concept input, `data/curated/concept_additions.jsonl`. One row per concept:
    a manual source key (`manual:can-be-able`), slug, lexfile (`verb.modal` or the nearest
    `verb.*`), the en gloss and en members (*can*, *be able to*). The build creates the concept
    with `definition_sources` tagged `manual`. Latest row wins per key. It adds no field to the
    frozen API, so it is a minor release.
  - b. Link to the nearest WordNet concept (the adjective "able"). No code, but a near miss: the
    card teaches an adjective for a verb.
  - c. Leave the modals out of the drill.
  - Recommended: a, because these are among the most frequent verbs in any language, and the
    input is the same pattern as the other curated rows.
  - ANS: a (user, 2026-11-09).
- Q3: Which modal concepts. pt *poder* covers ability and permission ("I can swim", "you may go");
  *dever* covers obligation and likelihood ("you must go", "it must be late"), and its
  conditional *deveria* is English "should".
  - a. Two concepts: "be able to, can, may" and "must, have to, be obliged to". *poderia* "could"
    and *deveria* "should" are forms of them, with a form note.
  - b. Four: ability, permission, obligation, likelihood.
  - c. Three: a. plus "should, ought to" for advice.
  - Recommended: a, because a card teaches a word and pt has one verb for each pair; c. is the
    alternative if *deveria* should teach "should" on its own.
  - ANS: a (user, 2026-11-09, with a question mark: open to revisit when the cards are seen).
- Q4: Which twin the numbers link to. Every number has the adjective "denoting a quantity of 12
  items" (how the word is used: *doze ovos*) and the noun "the cardinal number 12".
  - a. Link both and pin the adjective; bring the 22 present numbers to the same shape.
  - b. Link and pin the noun only, the shape most present numbers have.
  - c. Follow the rulebook's twin tie-break word by word.
  - Recommended: a, because the word means both and the adjective is how it is used. The
    present numbers' mixed links (*seis* on "six-spot") would also be fixed.
  - ANS: a (user, 2026-11-09).
- Q5: Which forms get a lemma. The modal forms run to about 30 above zipf 4, with more below.
  - a. Every form in the pt `wordfreq` top 5,000, each linked to its modal concept with a form
    note (`3rd person singular present of "poder": he/she can`).
  - b. Only the forms in the pt top 1,000.
  - c. The infinitive only. *poder* and *dever* get the card, and the forms stay absent.
  - Recommended: a, because a learner meets these forms far more often than the infinitive
    (*pode* 6.2 against *poder* 5.6), and the form note teaches the form, as it does for
    *são*, *vão*, *tinha* in `13_missing_senses`.
  - ANS: a (user, 2026-11-09), tied to Q1: if the wider gap becomes a phase, the same cut-off
    applies there.
- Q6: Measurement and labelling. The user's rule is that a decision rests on 500+ targeted
  items, but both groups together are about 70 words, the whole population.
  - a. I label all of them by hand, as I did the 32 glosses, write the full list into the phase
    sub-plan for you to read, and check every card on the rebuilt corpus. Nothing is sampled
    because nothing is left out.
  - b. A subagent labels them under the rulebook and I review its labels.
  - Recommended: a, because the list is closed, short and mechanical. A review would only
    repeat it.
  - ANS: all labelled by hand through agents (user, 2026-11-09): subagents label under the
    rulebook, no paid LLM job; I check every label and every rebuilt card.
