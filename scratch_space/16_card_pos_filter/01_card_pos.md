---
status: done
---

# Phase 1 - part of speech of a card

## Overview

A lemma's part of speech is the class most of its WordNet synsets have, so *um* is a noun while its card is
the article "a, an". Make the pinned card set it (Q3), before the filter reads it.
Context: [`00_start.md`](00_start.md) Q3, Q4.

## Plan

- A build step after the best-sense pins: every lemma whose pin is on a concept with a known
  class (`sense_additions.LEXFILE_POS` of its lexfile) takes that class (Q3 a).
- Test on the seed; `docs/library/lexicon.md` says where a lemma's part of speech comes from.
- Rebuild, gate, `make check`. Before and after: the part-of-speech counts, the look-alike
  edges and stale rows, the stale pins.
- Read the changed lemmas (90 expected) on 8010.
- Assess the unpinned lemmas (Q4 a): how many have a part of speech other than the class of
  their card sense, by band of frequency, with examples; reported here, not changed.

## Pitfalls

- The build applies look-alike rows by lemma id only (`apply_lookalikes`), so the built edges
  cannot change; `cognate_key` reads the part of speech only when a new worklist is mined, where
  a lemma that turned verb is matched by its infinitive. The counts are still compared.
- A pin on a concept whose lexfile has no class in `LEXFILE_POS` leaves the lemma as it is.

## Done when

- *um* and *uma* are determiners, the changed lemmas read right, look-alike counts explained,
  gate and `make check` pass.

## What the implementation found

- Plan review: the build applies look-alike rows by lemma id only, so the built edges could not
  change (corrected above); a lemma's class is the majority of its synsets, not the first.
- `best_senses.apply_pinned_part_of_speech` runs right after the pins; the manifest records
  `part_of_speech_changed`. Build: 90 pt lemmas changed, as measured, and nothing else moved:
  look-alikes 6,839 with 8 stale, 724 pins with 0 stale. Report: determiners 69 to 71.
- All 90 read on 8010 (`01.1_measure_pos.py`): each class is its card's. *um*, *uma*
  determiner; *hoje*, *lá*, *bem*, *mal* adverb; 18 forms turned verb (*era*, *são*, *visto*);
  the numbers adjective, the twin `14_number_modal_words` pinned.
- Q4, unpinned pt lemmas whose class is not their card's: 26 of 470 in the top 1,000 (*não*,
  *ser*, *saber* noun), 69 of 1,984 in 1,001 to 5,000, 134 of 5,077 in 5,001 to 20,000,
  211 of 37,939 beyond; 440 of 45,470 in all, about 1%. None is a function word, so the filter
  is not affected. Not changed (Q4 a).
- `make check` 470 passed, gate PASS, docs build.
