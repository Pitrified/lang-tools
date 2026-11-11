# implementation tracking

Give the frequent inflected pt forms (*anos*, *foi*, *boa*) a lemma on their base word's meaning,
with a form note, from our own inflection rules applied at build instead of one reviewed row per form.
Analysis and decisions in [`00_start.md`](00_start.md).

## Key decisions

- Our own rules generate the forms; kaikki only measures them, in the scratchpad (Q1 b).
- The model fills only the forms the build lacks; every reviewed row wins (Q5 a).
- One base per form (Q4 a); a form copies that base's senses of the form's class and its pin, so its
  card is its base's card with a label-only note (Q6 a).
- Forms of zipf 3.0 and up (Q3 c), out of card queries unless asked for (Q2 b).

## Phases

| #  | Phase                       | Plan                                       | Status      |
| -- | --------------------------- | ------------------------------------------ | ----------- |
| 1  | Form generator and measure  | [`01_form_table.md`](01_form_table.md)     | done        |
| 2  | Build stage                 | [`02_build_stage.md`](02_build_stage.md)   | planned     |
| 3  | Card filter for forms       | [`03_card_filter.md`](03_card_filter.md)   | planned     |
| 4  | Release v0.7.0              | [`04_release.md`](04_release.md)           | planned     |

Status values: draft / planned / in progress / done / superseded / discarded.

## Log

Append-only. Newest at the bottom.

- 2026-11-10 : draft folder spun off from `14_number_modal_words` Q11 b.
- 2026-11-11 : picked up. Merged main (v0.6.0) into the branch, which was cut at v0.4.0.
  Assessed three sources in the scratchpad: UniMorph `por` (verbs only), the kaikki pt extract
  (form-of senses for nouns, adjectives and verbs; 351,303 forms) and the ending rules of
  `14_number_modal_words`. kaikki finds the reviewed base for 363 of the 421 reviewed form words,
  the rules plus UniMorph 312; the misses are nearly all closed-class words. At zipf 3.0, 10,834
  absent pt forms have a base the corpus has. kaikki serves only its latest extract. Q1 to Q8
  raised, phases 1 to 4 drafted.
- 2026-11-11 : Q1 to Q8 answered (b, b, c, then a, a, a, a, b as recommended) and folded in. Q1 b
  (own rules, kaikki only to measure) rewrote the approach and phase 1, and made Q8 moot.
- 2026-11-11 : phase 1 started. Review: the claim that a wrong generated form can only be a
  non-word was too strong (a regular form of a rare verb can spell a real word); corrected, the
  kaikki measure covers it. Nothing else to correct.
- 2026-11-11 : phase 1 done. `ingestion/inflections.py`: our own pt paradigms (regular, spelling
  and stem changes, 28 irregular verbs and their compounds), noun and adjective rules, the base
  pick and the form note; 75 tests. At zipf 3.0: 12,395 new forms; kaikki gives the same or an
  equivalent base on 12,102 (98%), 205 have no kaikki analysis, 88 differ (mostly kaikki
  listing only a verb reading; about 7 model errors). 326 of 347 reviewed content forms get the
  reviewed base. A finite-form rule was tried and removed (it broke *completa*, *viva*). English
  look-alikes (183) and names (140) are kept, with counts. `make check` 547.
