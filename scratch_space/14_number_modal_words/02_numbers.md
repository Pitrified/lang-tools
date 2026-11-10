---
status: done
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

## What the implementation found

- The closed-class list took 20 of Q8's 21: *devido* stays off, since it is also the
  adjective "due" (*o devido respeito*). *uma* came off, which the build shows as one sense and
  one lemma fewer dropped (230 and 117).
- The cardinal check found 53 words above zipf 3, 26 absent. Labels (one subagent, about 71k
  tokens): 66 adds, 5 pins, 6 drops, 8 skips. Two decisions beyond the plan:
  - Brazilian *bilhão* is 10^9 and *trilhão* 10^12, so their long-scale links (10^12, 10^18)
    were dropped; Portugal's *biliões* links the long-scale twins with a note.
  - *seiscentos*, *setecentos*, *oitocentos* have no WordNet concept and stay out;
    *cinqüenta* waits for Q10.
- Content words (one subagent, about 69k tokens): 31 words, 29 adds, 5 skips. *estadual*,
  *paulista*, *carioca* and *afro* have no concept that is their meaning; *segunda* takes the
  ordinal as its card and Monday as a second sense.
- The labellers reported wrong pt members, applied by hand as 22 drops: *osenhor* on
  thousand, *metrô* on the metre and three meters, four "comics" words on comedian, the
  misspellings *fèbre*, *diáriamente*, *rápidamente*, *assintência*, *dazassete*,
  *cinqüênta*, and *trilhão* on the long-scale billion.
- Most of the "missing" content words were spelling, not absence: Q10. They wait for it.
- Labels are applied by [`02.1_apply_labels.py`](02.1_apply_labels.py), which checks every
  line against the built corpus first and writes nothing unless all pass.
