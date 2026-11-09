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

## Phases

| #  | Phase                 | Plan                                         | Status  |
| -- | --------------------- | -------------------------------------------- | ------- |
| 1  | Gap assessment        | [`01_gap_assessment.md`](01_gap_assessment.md) | done    |
| 2  | Number words          | [`02_numbers.md`](02_numbers.md)             | planned |
| 3  | Curated concepts      | [`03_concepts.md`](03_concepts.md)           | planned |
| 4  | Modal verbs           | [`04_modals.md`](04_modals.md)               | planned |
| 5  | Release v0.5.0        | [`05_release.md`](05_release.md)             | planned |

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
