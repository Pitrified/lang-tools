---
status: planned
---

# Phase 1 - assess the wider gap

## Overview

Measure what the absent frequent pt words are, before deciding whether they become a later
phase of this folder.
Context: [`00_start.md`](00_start.md) Q1, Q5.
Read-only: it writes nothing but a scratch report and this file.

## Plan

- The absent words of the pt `wordfreq` top 1,000, 2,000 and 5,000 (first count: 366, 730 and
  2,222; alphabetic tokens only).
- Classify each absent word of the top 2,000 into one group, by rule first and by hand for the
  rest:
  - closed-class, dropped on purpose by `closed_class.py` (*de*, *que*, *eu*, *uma*);
  - an inflected form whose base word has a lemma (*tem* of *ter*, *anos* of *ano*), by a
    lookup of candidate base forms in the corpus;
  - an inflected form whose base word has none either;
  - a name, an English word, or a fragment (*paulo*, *the*, *http*);
  - a content word the sources lack (*cinco*, *ninguém*).
- The same split on a sample of the 2,001 to 5,000 band, to see whether its mix differs.
- Write the table here, with examples per group, and raise the follow-ups as new questions in
  `00_start.md`: which groups a later phase covers, and how (per-word additions with form
  notes, or an inflection model; closed-class words stay out under the rule unless a group
  argues otherwise).

## Out of scope

- Adding any of these words. Numbers and modals are phases 2 to 4; the rest waits for the
  answers.

## Done when

- The counts per group for the top 1,000 and 2,000, and the 2,001 to 5,000 sample, are written
  here, with the new questions in `00_start.md`.
