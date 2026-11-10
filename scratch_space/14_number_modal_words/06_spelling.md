---
status: planned
---

# Phase 6 - pre-reform spelling

## Overview

The pt wordnet spells about 225 single-word lemmas as before the 2009 orthography reform
(*idéia*, *seqüência*, *vôo*), and a few are misspelt (*qüestão*, *juíz*, *raíz*).
`wordfreq` counts today's spelling, so those cards rank low or vanish, and the modern word
looks absent.
Respell them at build with a deterministic rule, as the closed-class rule drops function words
(Q10 a).
Context: [`00_start.md`](00_start.md) Q10; [`01_gap_assessment.md`](01_gap_assessment.md).
Before phase 7, so the closed-class concepts are written against the final lemma ids.

## Plan

- Measure first, on the built corpus and the OMW pt entries: the lemmas each rule touches,
  the old/new pairs that both exist (12 seen in phase 1), and the curated rows (sense drops,
  additions, pins, look-alikes, member-form drops) keyed on an old lemma id. Report the counts
  before writing code.
- Rules, pt only, applied to a lemma text:
  - trema dropped (*ü* to *u*: *seqüência*, *tranqüilo*, *agüentar*);
  - *éi* / *ói* unaccented in a paroxytone (*idéia*, *assembléia*, *jóia*), not in an oxytone
    (*papéis*, *herói* keep the accent);
  - *ôo* to *oo* (*vôo*, *enjôo*), *êem* to *eem* (*lêem*, *vêem*);
  - a short table of misspellings and the differential accents the reform removed (*pára*,
    *pêlo*), each entry checked by hand, since a rule cannot tell *pára* the verb from *para*.
  Each rule only fires when the modern spelling is more frequent in `wordfreq` than the old one,
  so a word the rule misreads stays as it is.
- A build stage right after the transform, before anything keys on a lemma id: respell the
  lemma, and merge it into the modern lemma when both exist (senses united, sources kept). The
  manifest counts respelt, merged and skipped lemmas.
- Curated rows keyed on an old lemma id: re-key them in the same stage, or migrate the files
  once with a script, whichever the measurement shows is smaller; zero stale rows either way.
- Tests on the seed, the rule in `docs/library/lexicon.md`, rebuild, gate, and every card of
  the frequent modern spellings (the 53 above zipf 3, plus *ideia*, *questão*, *juiz*) read on
  8010. *cinqüenta*, held in phase 2, comes back as *cinquenta*.

## Out of scope

- Other languages' spelling variants.
- European / Brazilian spelling differences that are not pre-reform (*facto* / *fato*).

## Done when

- The measured lemmas are respelt or listed as skipped with the reason, 0 stale rows,
  `make check` and the gate pass, and the listed cards were read.
