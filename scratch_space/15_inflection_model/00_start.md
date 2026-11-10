---
status: draft
priority: 0
description: |
  An inflection model for pt (and later the other languages): map an inflected form
  (*anos*, *foi*, *disse*) to its base word's card with a form note, by rule or table at
  build, instead of one reviewed row per form.
comment: |
  Spun off from 14_number_modal_words (on feat/14_number_modal_words), 00_start.md Q7 b and
  Q11 b.
---

# Inflection model

## Origin

`14_number_modal_words` (branch `feat/14_number_modal_words`) found that the largest group
of frequent pt words absent from the corpus are inflected forms of a word the corpus has:
197 in the pt top 1,000, 262 in the 1,001 to 2,000 band, and about 1,300 in the top 5,000.
Its phase 5 gave the 187 forms of the top 1,000 a lemma each, linked to the base word's
concept with a form note (`plural of "ano": years`), through reviewed `sense_additions` rows
written by subagents. Every card came out right, but each form cost about 1,200 subagent
tokens and a checked line; the top 5,000 would be about 1.6M tokens, 5% to 10% of a weekly
limit, and the cost grows linearly with every form.
The user chose the model before any more rows (`14_number_modal_words/00_start.md` Q11,
answered b, 2026-11-10).

## The idea

A form is found and tagged by rule or table, not reviewed one at a time:

- generate or look up the forms of a base word (pt verb conjugation, noun and adjective
  plural and gender), with the grammatical label that becomes the form note;
- at build, link each frequent form to its base word's card (or to the concept a reviewed
  row chose, where the form means something else: *todos* "all", *pais* "parents");
- search: a learner typing *foi* finds *ser* and *ir*.

## To assess when this is picked up

- Sources: a morphology table (Wiktionary extracts, UniMorph, a conjugator such as `verbecc`
  or `mlconjug3`), a rule set, or both; licence and coverage for pt first.
- Ambiguous forms (*foi* is *ser* and *ir*; *fui*; *vem*/*vêm*): one card or several.
- How the phase 5 rows of `14_number_modal_words` relate: kept as overrides, or replaced.
- Whether a form gets its own lemma (as now) or is a field of the base lemma.
- Scope: pt only first, the other languages later.

## Open questions

None yet: raised when the folder is picked up.
