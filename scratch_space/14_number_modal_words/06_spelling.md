---
status: done
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
  - trema dropped from *gue*, *gui*, *que*, *qui* (*seqüência*, *tranqüilo*, *agüentar*), a
    foreign *ü* kept (*Dürer*);
  - *éi* / *ói* unaccented in a paroxytone no other rule accents (*idéia*, *assembléia*,
    *jóia*), not in an oxytone (*papéis*, *herói*), a proparoxytone (*géiseres*) or a
    paroxytone in *-r* (*destróier*); word by word inside a multi-word lemma;
  - *ôo* to *oo* (*vôo*, *enjôo*), *êem* to *eem* (*lêem*, *vêem*);
  - a short table of misspellings and the differential accents the reform removed (*pólo*,
    *pêra*), each entry checked by hand; *pêlo* is left out, since respelt it is the
    closed-class *pelo*.
  No frequency gate: the measurement showed `wordfreq` counts the old spelling higher for 55 of
  the respelt words (*paranóia*, *heróico*, *bóia*), all of which the rule gets right.
- The last pass of `spelling_noise_folds`, which maps a member form to its canonical form
  before lemma ids are minted, so a respelt form merges with the modern one when both exist,
  and nothing downstream sees the old spelling. The fold log line counts it with the other
  folds.
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

## What the implementation found

- The plan review corrected three claims before any code (written into the plan above): the
  frequency gate would have left 55 words in the old spelling; the trema rule had to be limited
  to *gu* / *qu* (the first pass touched *Dürer*, *Lübeck*); the diphthong rule had to work word
  by word and spare the oxytones inside a phrase (*lençóis freáticos*, *Fiéis*) and the
  paroxytones other rules accent (*destróier*, *géiseres*).
- The existing lost-accent fold made things worse, not better: where both spellings share a
  concept it folded the modern word into the old one (*ideia* into *idéia*, more marks). The
  respelling therefore runs last and respells the fold targets too.
- 299 pt lemmas respelt by the rules plus 6 by the table, every one read by hand; 12 merged
  into an existing modern lemma (46,077 to 46,066 pt lemmas). The curated rows keyed on an old
  lemma were all look-alikes: 56 reviewed, 415 worklist and 3 gold rows, re-keyed once by
  `06.2_migrate_curated.py`, so look-alikes stay at 11 stale and every other input at 0.
  *consequência*, added by hand in phase 2, now also comes from the wordnet.
- Every respelt word with a modern zipf of 3 or more (84) and the 6 table words read on 8010:
  each has its card under the modern spelling, and the old spelling is gone. *cinquenta* is
  back as "fifty".
- Words that were rare under the old spelling were outside the card review of the top 1,000;
  8 of them showed a wrong card and were fixed by hand (`14_respelt_cards.labels.txt`):
  *aguentar* "put up with", *questionar* "call into question", *raiz* the plant root, *polo*
  the Earth's pole, *sequência* "sequence", *sequestrar* "kidnap", and two added senses,
  *plateia* "audience" and *enjoo* "nausea" (its "illness" link dropped).
- `make check` 468 passed, docs build, gate PASS; 596 pins, 0 stale.
