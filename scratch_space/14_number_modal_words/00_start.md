---
status: in progress
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
2. Numbers and content words: the missing content words of the top 5,000 (Q9) and the
   function words onto the closed-class list (Q8) go with the numbers. Add the 20 missing words, labelled by subagents and applied with `add` (Q6), on the twin chosen in Q4, with a
   form note where the word is a form (*uma* the feminine of *um*, *milhões* the plural of
   *milhão*), and bring the present numbers onto the same twin.
3. Curated concepts: a new curated input that creates a concept the sources lack, keyed on a
   stable manual source key, with an English gloss and English members, applied at build before
   the sense additions so an addition can link to it (Q2).
4. Modal verbs: the concepts from Q3, *poder* and *dever* linked to them and pinned, their forms
   added with form notes (Q5).
5. Inflected forms: the forms of the top 1,000 whose base word has a lemma (Q7), with form
   notes.
6. Release v0.5.0 and bump lang-tutor's pin.

Steps 2 to 5 each end with a rebuild and the gate, as in `13_missing_senses`.

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

Raised by phase 1 ([`01_gap_assessment.md`](01_gap_assessment.md)), 2026-11-09:

- Q7: Inflected forms. About 1,500 forms in the pt top 5,000 lack a lemma while their base word
  has one (*tem* of *ter*, *anos* of *ano*, *boa* of *bom*); about 200 of them are in the top
  1,000. Today a form gets a card only through its own addition row with a form note (*são*).
  - a. Per-word rows for the forms in the top 1,000 (about 200), found by the phase 1 rules,
    labelled by subagents with a form note, as phases 2 and 4 do for numbers and modals.
    The forms beyond wait for b.
  - b. An inflection model: a curated form table (form, base lemma, features such as "3rd
    person plural present"), applied at build, from which the form notes and lookups come. A
    form is found by search and tagged on its base word's card; it is not a card of its own.
    A later phase with its own questions: source of the table, how lang-tutor shows it.
  - c. Leave the forms out: cards are base words.
  - Recommended: a now as phase 6, and b raised again when phase 6 is done, because a is
    the pattern the corpus already has and covers the forms a learner meets first, while 1,500
    rows by hand would be the wrong tool for the rest.
  - ANS: a (user, 2026-11-09): phase 5, the forms of the top 1,000; b raised again after it.
- Q8: Function words. 21 frequent function words are on no list (*tudo*, *qualquer*,
  *ninguém*, *algo*, *algum*, *quanto*, *quantos*, *quantas*, *ambos*, *tais*, *disso*,
  *nisso*, *daqueles*, *através*, *apesar*, *entanto*, *devido*, *dentre*, *redor*, *exceto*,
  *quê*). Phase 3's curated concepts would also make the closed-class rule's premise optional
  ("no WordNet concept, so no card"), and the 117 closed-class words of the top 1,000 (*eu*,
  *você*, *de*, *que*) are the most frequent words of the language.
  - a. Add the 21 to the closed-class list; the policy is unchanged.
  - b. Give closed-class words curated concepts and cards, pronouns and quantifiers first
    (*eu* "I", *tudo* "everything", *ninguém* "nobody"), a later phase reusing phase 3.
  - c. a now, and b assessed once phase 3 exists.
  - Recommended: c, because a keeps the rule consistent at no cost, and b is a change of
    policy that is better judged with the curated-concept input in hand.
  - ANS: c (user, 2026-11-09): the 21 go on the list in phase 2; b is raised again after
    phase 3.
- Q9: The missing content words (11 found: *cinco*, *nove*, *questão*, *ideia*, *juiz*,
  *assembleia*, *rapidamente*, *estadual*, *paulista*, *bíblia*, *carioca*; the sample suggests
  about 10 more in the 2,001 to 5,000 band).
  - a. Phase 2 takes them along with the numbers: the full top 5,000 residue sorted by hand
    (the 1,192 unsampled words of the band run through the classifier first), each linked
    to its en concept by a subagent.
  - b. Only the 11 found.
  - Recommended: a, because the classifier leaves a short residue, and phase 2 already has the
    tooling and the review.
  - ANS: a (user, 2026-11-09): phase 2.

Raised during phase 2, 2026-11-09:

- Q10: Pre-reform spelling. The pt wordnet spells words as before the 2009 orthography reform:
  225 single-word lemmas (*idéia*, *assembléia*, *seqüência*, *tranqüilo*, *vôo*, *jóia*),
  of which 134 are less frequent in `wordfreq` than their modern spelling and 53 have a modern
  spelling above zipf 3. It also has a few misspellings (*qüestão*, *juíz*, *raíz*). This is
  why *ideia*, *questão*, *juiz*, *assembleia*, *sequência*, *tranquilo* and *aguentar* looked
  missing in phase 1: their meaning is in the corpus under the old spelling, a lemma
  `wordfreq` barely sees, so its card is rare or absent. 12 lemmas exist in both spellings.
  - a. A deterministic spelling rule at build, like the closed-class rule: right after the
    transform, before anything keys on a lemma id, respell a pre-reform lemma (trema dropped,
    *éi* / *ói* in a paroxytone unaccented, *ôo*, *êem*) plus a short table of misspellings,
    and merge it into the modern lemma when both exist. Curated rows keyed on an old lemma id
    are migrated in the same step (counted first). A phase of its own, before phase 5.
  - b. Per-word additions for the 53 frequent modern spellings, linked to the old spelling's
    concepts; the old lemmas stay, so a word can have two cards.
  - c. Leave it; the cards stay under the old spelling.
  - Recommended: a, because the rule is mechanical and fixes the whole class at once, the way
    the closed-class rule does; b duplicates cards and has to be redone for every new word.
  - NEW_ANS:

Raised at the end of phases 2 to 5, 2026-11-09:

- Q11 (Q7 b again): an inflection model for the forms beyond the top 1,000. Phase 5 cost about
  1,200 subagent tokens and one checked line per form, and every card came out right; the
  forms of the top 5,000 would be about 1,300 more (about 1.6M tokens, 28 batches of 47).
  - a. Continue with rows: the forms of the 1,001 to 2,000 band next (about 260), same method.
  - b. Design the inflection model (a form table applied at build; a form found by search and
    tagged on its base word's card) as the next folder, and stop adding form rows here.
  - c. Stop at the top 1,000 for now.
  - Recommended: c, then b: the top 1,000 covers the forms a learner meets first, and rows past
    it scale linearly while a model would cover every form at once.
  - NEW_ANS:
- Q12: Base words with a wrong card, found while labelling their forms: *rede* "cloth" (it is
  "net, network"), *graça* "joke" ("grace", *de graça* "free"), *atividade* "action"
  ("activity"), *receber* "get, acquire" ("receive"). None is among the 1,000 cards the card
  review covered.
  - a. A card-sense re-check of these four now, through the `sense-review` skill.
  - b. Extend the card-sense review to the pt cards ranked 1,001 to 2,000, which would catch
    these and their like, as its own measured run.
  - Recommended: a now (small, clear), and b raised when the next card-review run is planned.
  - NEW_ANS:
- Q8 b, as its answer asked, now that phase 3 exists: closed-class words could get cards
  through curated concepts (*eu* "I", *tudo* "everything", *ninguém* "nobody"). Not raised as a
  question yet: it is a policy change for the 117 most frequent words, best opened as its own
  plan once Q10 and Q11 are settled. Noted here so it is not lost.
