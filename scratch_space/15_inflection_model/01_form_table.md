---
status: done
---

# Phase 1 - pt form generator and its measure

## Overview

Write our own pt inflection rules (Q1 b), and measure them against kaikki and the reviewed forms
before any build reads them.
Context: [`00_start.md`](00_start.md) Q1, Q4, Q6. Rewritten after Q1 b: the first draft parsed a
kaikki table.

## Goals

1. A pure generator: base word and class -> forms with tags; the irregular verbs as a table in the
   code.
2. The analysis: the absent frequent forms -> one picked base and a form note.
3. A measured answer on 500+ forms: does the model's base and label agree with kaikki's, and with
   the 421 reviewed form words.

## Plan

- `src/lang_tools/lexicon/ingestion/inflections.py`, standard library only:
  - `FormTags` (person, number, tense, mood, gender, plus `participle`, `gerund`, `infinitive`);
  - `noun_forms(base)`: the plural (*ano* -> *anos*, *mês* -> *meses*, *animal* -> *animais*,
    *papel* -> *papéis*, *homem* -> *homens*, *nação* -> *nações*; the -ão words take the -ões
    plural, with a short list of -ães and -ãos ones);
  - `adjective_forms(base)`: the feminine (*novo* -> *nova*, *português* -> *portuguesa*,
    *trabalhador* -> *trabalhadora*, invariable *feliz*, *grande*; a table for *bom*, *mau*) and
    both plurals;
  - `verb_forms(base)`: the regular paradigms, the spelling changes, the -ir stem changes, the
    irregular table; pt-BR and pt-PT forms both (*falamos*, *falámos*);
  - `form_note(base, readings)`: the house-style label, readings of one tense merged by person;
  - `analyse(bases, zipf, floor)`: invert the generated forms, keep those at or above the floor,
    apply Q4 a, and a base that is itself a generated form of another base gives way to it.
- Measure (scratch `01.1_measure_forms.py`, reading the scratchpad kaikki index): for every model
  form at zipf 3.0, whether kaikki has the same base, and the same tense and person; the forms
  kaikki has that the model misses, by kind; the 421 reviewed form words against the model.
  Every disagreement class gets a count and examples; the rules are fixed until what remains is
  explained.
- Unit tests for each paradigm on the irregular and spelling-change verbs, the noun and adjective
  rules, the note writer and the base pick.

## Out of scope

- The build stage (phase 2) and the card filter (phase 3).
- Languages other than pt.
- Clitic forms (*fazê-lo*), diminutives and superlatives: they are not inflection in the sense of
  the reviewed rows.

## Done when

- The measure is in "What the implementation found" with every disagreement class explained, the
  base agreement with kaikki is reported on all model forms at zipf 3.0, and `make check` passes.

## What the implementation found

- `src/lang_tools/lexicon/ingestion/inflections.py`, standard library only, with 75 unit tests.
  The approach held; the plan's "`FormTags`" became a `Reading` (base, class, kind, person,
  number, gender), and `analyse` does the inversion and the pick in one pass.
- Measured by `01.1_measure_forms.py` on the v0.6.0 corpus, with the reviewed form words treated
  as absent. At zipf 3.0 the model gives 12,395 forms beyond the 342 reviewed words it also
  finds: 7,196 verb, 2,765 noun and 2,434 adjective forms.
- Against kaikki (scratchpad only), on all 12,395:
  - the same base on 11,796;
  - an equivalent base on 306, a participle used as a word or a gender twin (*interessada* of
    *interessado*, where kaikki says *interessar*);
  - no usable kaikki analysis on 205;
  - another base on 88. Read in full, most are kaikki listing only a rare verb reading (*lutas*,
    *marcas*, *pesquisas* as "you fight"), so the model's noun plural is right. A sample of 25
    had 2 model errors (*destina* of the noun *destino*, *basta* of *basto*), about 7 in all.
  So about 98% of the model forms have the base kaikki gives or an equivalent one.
- Against the 421 reviewed form words: 74 are closed-class words, left to their rows. Of the 347
  others, 326 get the reviewed base.
  - 5 get another base: *completa* (*completo*, the row says *completar*), *viva*, *termos*
    (*ter*), *usada* (*usado*), *última* (*último*; the row's base is misspelt *ultimo*). All
    defensible except *termos*.
  - 16 get no form: the closed-class words' feminines (*alguma*, *duas*, *muitas*; their bases
    have no noun or adjective sense), *máxima* and *terceira* (bases with noun senses only),
    *milhares* (no noun sense on *milhar*), *baseado* (no verb *basear* in the corpus), and
    *cento*, *dezasseis*, *dezassete*, *tá*, which are not inflections.
  The reviewed rows win at build (Q5 a), so none of these changes a card.
- kaikki forms the model lacks at zipf 3.0, 140 in all: diminutives and augmentatives
  (*cantinho*, *carrão*), English plurals (*hackers*), imperatives (*sê*, *vinde*), colloquial
  *tá* and *tás*, and a few person-noun feminines (*patroa*, *macaca*). All are out of scope by
  design.
- Rules the measure added, each checked again on the full set: the -uzir 3rd singular (*produz*),
  accented stressed stems (*reúne*, *proíbe*), the hiatus plural *raízes*, *nu*/*nua*,
  *afegãos*, feminines of nouns naming a person (lexfile `noun.person`: *bióloga*,
  *professora*), the participle compounds of *escrever* (they are *in*+*screver*, not
  *in*+*escrever*), and a verb giving way to its feminine participle used as a noun (*comidas*,
  *medidas*).
- One rule was tried and removed: an adjective spelled like a finite verb form gives way to the
  verb. It fixed *precisa*, but broke *completa* and *viva*, and *precisa* has a reviewed row.
- 1,025 forms have strong readings of several bases; kaikki agrees with the pick on 708, and most
  of the rest are participle and adjective twins.
- Two kinds of form are kept, with the counts recorded:
  - 183 model forms are as frequent in English as in Portuguese, so their pt zipf is partly
    English (*to*, *for*, *some*, *times*, *classes*). Most are real pt forms (*for* of *ser*,
    *times* "teams"); *to* and *does* are noise.
  - 140 are also names in kaikki (*gomes*, *castro*, *domingos*, *irão*); most are real forms
    too.
  Forms are out of drills by default (Q2 b), and a filter on either list would be a knob with no
  clean rule, so neither is filtered.
- 498 model forms also have a sense of their own in kaikki (Q7 a); phase 2 lists them.
