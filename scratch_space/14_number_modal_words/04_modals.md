---
status: done
---

# Phase 4 - modal verbs

## Overview

Link *poder*, *dever* and their frequent forms to the two modal concepts.
Context: [`00_start.md`](00_start.md) Q3, Q5, Q6; depends on [`03_concepts.md`](03_concepts.md).

## Plan

- The list: every form of *poder* and *dever* in the pt `wordfreq` top 5,000 (Q5), found by a
  conjugation table checked against `wordfreq`, not guessed.
- One subagent labels the list (Q6): the concept, and a form note in the house style
  (`3rd person singular present of "poder": he/she can`; *poderia* `conditional of "poder":
  could`; *deveria* `conditional of "dever": should`). I check every line, then apply with
  `add`.
- *poder* and *dever* keep their noun and "owe" senses and are pinned to the modal concept,
  the frequent reading.
- Phase 3 ends with a rebuild, so `add` finds the two concepts (it checks the built corpus).
- Rebuild, gate, and read every card on 8010.

## Out of scope

- *ter que* / *ter de* "have to" (multi-word).

## Done when

- Every form in the list has a lemma on its modal concept with a form note, *poder* and *dever*
  are pinned, zero stale rows, the gate passes, each card was read.

## What the implementation found

- 28 forms of the two verbs are in the top 5,000, all absent; *devido* is left out (it is
  "due" and *devido a* "due to", not the modal).
- One subagent wrote the notes (about 45k tokens): 29 adds, the infinitives with no note and
  pinned over their nouns. Every card read on 8010 shows the modal meaning with its note.
