---
status: planned
---

# Phase 2 - number words, missing content words, the closed-class list

## Overview

Add the missing pt cardinals and bring the present ones to one shape (Q4), add the content
words the sources lack in the top 5,000 (Q9), and put the 21 unlisted function words on the
closed-class list (Q8).
Context: [`00_start.md`](00_start.md) Q4, Q6, Q8, Q9; [`01_gap_assessment.md`](01_gap_assessment.md).
No new code beyond the list: `add` writes a `sense_additions.jsonl` row, which creates a
missing lemma, and a pin.

## Plan

- The closed-class list (`closed_class.py`):
  - add the 21 function words of Q8. They have no lemma today, so the build changes nothing;
    the list keeps a later source from carding them and `add` from linking them;
  - take *uma* off the list. *um* is not on it (it is also "one"), and `add` refuses a
    closed-class word, so *uma* "one" could not come back otherwise. Its OMW senses, if any
    return, are read and dropped where wrong;
  - the module docstring names *um* / *uma* with the other homographs kept off the list.
- The numbers: the 20 absent cardinals and the 22 present, plus any other cardinal or spelling
  in `wordfreq` above zipf 3 (*duzentas*, *bilhões*, *zero*), checked by a script, not
  guessed.
- The content words: run `01.1_gap_classify.py` over the whole 2,001 to 5,000 band (it
  sampled 300), and I sort its residue by hand, as for the top 2,000. The missing content
  words of all three bands make the list.
- Labels (Q6): one subagent for the numbers and one for the content words. Each gets its list
  with the `concepts` command and the rulebook, and writes one line per action:
  `add <word> <key> [form note]`, `pin <word> <key>`, `drop <word> <key>`, with a reason.
  For a number: both twins added, the adjective last so it is the pin, a form note where the
  word is a form (*uma*, *duas*, *milhões*), and a present word's wrong links dropped (*seis*
  on "six-spot"). I check every line against the corpus, then apply them in one process
  through `add_sense`, `pin_sense` and `drop_sense`.
- Rebuild, gate, read every card of both lists on 8010.

## Out of scope

- Ordinals: present, except *segunda*, which is a weekday as much as an ordinal, so it goes
  to the content-word labeller.
- Compound numbers (*vinte e um*), which are not single-word cards.

## Done when

- Every pt cardinal above zipf 3 has a lemma linked to both twins with the adjective pinned;
  each listed content word has its link; the closed-class list holds the 21 and not *uma*;
  zero stale additions in `_build.json`; `make check` and the gate pass; each card was read.
