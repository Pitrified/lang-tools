---
status: draft
---

# Phase 1 - part of speech of a card

## Overview

A lemma's part of speech comes from its first WordNet sense, so *um* is a noun while its card is
the article "a, an". Make the pinned card set it (Q3), before the filter reads it.
Context: [`00_start.md`](00_start.md) Q3, Q4.

## Plan

- A build step after the best-sense pins: a lemma whose pin is on a concept with a known class
  (`sense_additions.LEXFILE_POS` of its lexfile) takes that class. Scope per Q3.
- Test on the seed; `docs/library/lexicon.md` says where a lemma's part of speech comes from.
- Rebuild, gate, `make check`. Before and after: the part-of-speech counts, the look-alike
  edges and stale rows (`cognate_key` reads the part of speech), the stale pins.
- Read the changed lemmas (90 expected) on 8010, and measure the unpinned mismatch (Q4).

## Pitfalls

- A lemma whose class changes to or from verb gets a different `cognate_key`, which can add or
  drop look-alike candidates; reviewed rows are keyed on lemma ids, so they should not go stale,
  but the counts are compared.
- A pin on a concept whose lexfile has no class in `LEXFILE_POS` leaves the lemma as it is.

## Done when

- *um* and *uma* are determiners, the changed lemmas read right, look-alike counts explained,
  gate and `make check` pass.
