---
status: planned
---

# Phase 2 - number words

## Overview

Add the 20 missing pt cardinals and bring the 22 present ones to one shape.
Context: [`00_start.md`](00_start.md) Q4, Q6. No code: `sense_additions.jsonl` rows create a
missing lemma, and `best_senses.jsonl` pins.

## Plan

- The list: the 20 absent cardinals in `00_start.md` and the 22 present, checked again against
  `wordfreq` for any other cardinal or spelling above zipf 3 (the feminine hundreds,
  *duzentas*; *bilhões*; *zero*).
- One subagent labels the whole list (Q6): for each word, the two twin concept keys (adjective
  "denoting a quantity of N", noun "the cardinal number N", from `concepts`), a form note
  where the word is a form (*uma* the feminine of *um*, *duas* of *dois*, *milhões* the plural
  of *milhão*), and for a present word the links it should lose (*seis* on "six-spot").
  It writes `add`, `pin` and `drop` lines; I check every line against the corpus, then apply.
- *uma* is on the pt closed-class list as the article, which drops all its senses; an addition
  runs after that drop and wins over it, so *uma* comes back on "one" only.
- Words above a thousand that WordNet has as a single concept only (*bilhão*) take the one.
- Rebuild, gate, and read every number card on 8010.

## Out of scope

- Ordinals (present except *segunda*, which is a weekday and an ordinal; left to phase 1's
  follow-ups).
- Compound numbers (*vinte e um*), which are not single-word cards.

## Done when

- Every pt cardinal above zipf 3 has a lemma linked to both twins with the adjective pinned,
  `_build.json` shows zero stale additions, the gate passes, and each card was read.
