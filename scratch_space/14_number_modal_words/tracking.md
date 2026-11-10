# implementation tracking

Give pt its missing number words and its modal verbs: about 20 cardinals and about 30 forms of
*poder* and *dever* have no lemma, and the modals have no concept to link to.
Analysis and decisions in [`00_start.md`](00_start.md).

## Key decisions

- Narrow for now (Q1 a): numbers and modals. The wider gap of absent frequent words is
  assessed in phase 1 and may become a later phase here, not a new folder.
- Modals get curated concepts (Q2 a), two of them, "can" and "must" (Q3 a).
- Numbers link both WordNet twins and pin the adjective (Q4 a).
- Every form in the pt top 5,000 gets a lemma with a form note (Q5 a).
- Labels by subagents, every line checked by me; no paid LLM job (Q6).
- The wider gap is mostly inflection (phase 1): the forms of the top 1,000 get rows here
  (phase 5, Q7 a); an inflection model is raised again after it (Q7 b).
- Missing content words of the top 5,000 join phase 2 (Q9 a); the 21 unlisted function words
  go on the closed-class list, and cards for closed-class words are judged after phase 3
  (Q8 c).

## Phases

| #  | Phase                 | Plan                                         | Status  |
| -- | --------------------- | -------------------------------------------- | ------- |
| 1  | Gap assessment        | [`01_gap_assessment.md`](01_gap_assessment.md) | done    |
| 2  | Numbers, content words | [`02_numbers.md`](02_numbers.md)            | done        |
| 3  | Curated concepts      | [`03_concepts.md`](03_concepts.md)           | done    |
| 4  | Modal verbs           | [`04_modals.md`](04_modals.md)               | done    |
| 5  | Inflected forms       | [`05_forms.md`](05_forms.md)                 | done    |
| 6  | Release v0.5.0        | [`06_release.md`](06_release.md)             | planned |

Status values: draft / planned / in progress / done / superseded / discarded.

## Log

Append-only. Newest at the bottom.

- 2026-11-08 : bootstrapped from `13_missing_senses` (03_recount.md, "Cards still wrong").
  Measured on the v0.4.0 corpus with `wordfreq`: 20 of 43 pt cardinals and every frequent form
  of *poder* / *dever* lack a lemma; the en number concepts exist as adjective/noun twins, the
  present pt numbers link to them inconsistently; WordNet has no modal concept. Wider finding:
  366 of the pt top 1,000 words have no lemma (Q1). Q1 to Q6 raised.
- 2026-11-09 : Q1 to Q6 answered and folded in; phases 1 to 5 written. Counted further: 730
  of the pt top 2,000 absent, 2,222 of the top 5,000, the deeper band mostly inflected forms.
  Part of the gap is deliberate: `closed_class.py` drops pt articles, prepositions and
  pronouns, *uma* among them (phase 2 adds it back as "one", since an addition wins over the
  drop).
- 2026-11-09 : phase 1 started. Plan review: no pt lemmatizer is installed (simplemma, spaCy,
  stanza absent), so the "lookup of candidate base forms" is a rule heuristic (plural and
  feminine table, verb endings against the corpus verbs, 26 irregular verbs); its precision
  measured on a sample instead. No other finding.
- 2026-11-09 : phase 1 done (`01.1_gap_classify.py`). Of the absent words: forms of a word the
  corpus has 54% of the top 1,000 and about 71% beyond (about 1,500 in the top 5,000);
  closed-class 32% of the top 1,000 and almost none beyond; names and English 8% rising to 26%;
  21 function words missing from the closed-class list; 11 content words missing. Rule
  precision about 93% on 90 forms, the misses mostly names. Q7 to Q9 raised.
- 2026-11-09 : Q7 to Q9 folded in (all recommendations): phase 2 widened to the missing content
  words and the closed-class list, new phase 5 for the forms of the top 1,000, release moved to
  phase 6. Plan review: `add` refuses a closed-class word, so *uma* "one" needs *uma* off the
  list (*um* is not on it); `add` checks the concept in the built corpus, so phase 4 follows
  phase 3's rebuild. Labels are applied in one process through `add_sense` / `pin_sense` /
  `drop_sense`, not one CLI call per line.
- 2026-11-09 : phase 2 started. Plan review: *devido* stays off the closed-class list (also
  "due"), so 20 of Q8's 21 go on; *uma* comes off. The cardinal check found 48 above zipf 3,
  26 absent (with *milhares*, *bilhões*, *trilhões*, the feminine hundreds). Sorting the
  content-word residue of the full 2,001 to 5,000 band found the pt wordnet's pre-2009
  spelling: 225 lemmas (*idéia*, *seqüência*, *vôo*) and misspellings (*qüestão*, *juíz*),
  behind most of the "missing" content words. Raised as Q10; the spelling-affected words wait
  for it, the numbers and the other content words go ahead.
- 2026-11-09 : phases 2 to 5 implemented (user: "implement"). Closed-class list +20, *uma* off;
  `ingestion.concept_additions` with tests and docs, the two modal concepts; subagent labels:
  numbers (85 lines), content words (34), modals (29), forms (195 in four batches), plus 22
  hand drops of wrong members; every line checked by `02.1_apply_labels.py --dry`, then
  applied. Two rebuilds (the modal adds need the concepts built): 2 concepts, 516 senses added,
  327 lemmas created, 584 pins, 0 stale; look-alikes stale 11 (+1, *rápidamente*, a dropped
  misspelling). Gate PASS, `make check` 440 passed, docs build. All 300 labelled words read on
  8010: each card is the labelled one. Subagent cost about 410k tokens. Q11 to Q12 raised;
  Q10 still open.
- 2026-11-10 : committed phases 2 to 5 (`4681752`). Q12 a done by hand: 4 pins and 4 drops
  (`14_base_cards.labels.txt`), rebuild 588 pins 0 stale, gate PASS, the 4 cards and their
  forms (*redes*, *recebeu*) read right on 8010. Q8 b raised as Q13, naming the two pieces of
  code that make the closed-class rule.
