---
status: done
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

## What the implementation found

Run with [`01.1_gap_classify.py`](01.1_gap_classify.py) on the v0.4.0 corpus: every absent
word of the top 2,000, and a random 300 of the 1,492 absent in the 2,001 to 5,000 band (seed
14). The rules group closed-class words, then forms whose base word the corpus has (a plural
and feminine table, verb endings tried against the corpus's verbs, a table of 26 irregular
verbs), then words more frequent in English. I sorted the 254 words they left or sent to
English by hand.
No pt lemmatizer is installed, so the rules are a heuristic: on a sample of 90 of their forms,
about 7% were wrongly grouped, mostly names that look like verb forms (*rui*, *gomes*,
*roger*, *neves*, *palmeiras*); a few more had the right group and a wrong base (*ganha* to
*ganho*, *estiver* to *estivar*).

| Group | 1-1,000 | 1,001-2,000 | 2,001-5,000 sample | Examples |
| --- | --: | --: | --: | --- |
| form of a word the corpus has | 197 | 262 | 213 | *tem*, *anos*, *pode*, *boa*, *fiquei*, *conheço* |
| closed-class, dropped by the rule | 117 | 15 | 2 | *de*, *que*, *eu*, *você*, *uma* |
| name or place | 13 | 34 | 50 | *paulo*, *brasil*, *lisboa*, *benfica* |
| English, foreign, abbreviation, typo | 18 | 36 | 28 | *the*, *twitter*, *sp*, *nao*, *acção* |
| function word not on the closed-class list | 13 | 6 | 2 | *tudo*, *qualquer*, *ninguém*, *algo*, *através*, *dentre* |
| form of a word the corpus lacks | 3 | 4 | 1 | *boas*, *questões*, *ideias*, *milhares* |
| content word the sources lack | 3 | 6 | 2 | *cinco*, *nove*, *questão*, *ideia*, *juiz*, *assembleia*, *rapidamente*, *bíblia* |
| interjection | 2 | 1 | 2 | *oi*, *ah*, *né*, *caramba* |
| total absent | 366 | 364 | 300 | |

Read:

- **Most of the gap is inflection.** 54% of the absent top 1,000 and about 71% beyond are forms
  of a word the corpus has. Scaled to the whole band, that is about 1,500 forms in the top 5,000.
  Today each would need its own `sense_additions.jsonl` row with a form note, as *são* has.
- **The closed-class rule explains a third of the top 1,000**, and almost nothing beyond:
  deliberate, under today's rule that a word with no WordNet concept gets no card.
- **Names and English stay out**: proper nouns are capitalised lemmas and never cards
  (`13_missing_senses/00_start.md` Q2), and English is not pt. They grow with the band (8%,
  19%, 26%).
- **A short list of function words is missing from the closed-class list** (21 found), which
  leaves them neither dropped nor carded.
- **Few real content words are missing**: 11 found, two of them numbers phase 2 covers.
  The 2,001 to 5,000 count is a 300-word sample, so the band holds about 10 more.

The follow-ups are `00_start.md` Q7 to Q9.
