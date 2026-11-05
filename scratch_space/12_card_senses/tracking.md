# card senses - implementation tracking

Make the most frequent drill cards teach the right meaning: two build rules and an agent review
of the top cards that drops wrong concept links and pins the right best sense. Origin, causes
and open questions in [`00_start.md`](00_start.md).

## Key decisions

- All four causes are fixed (lang-tutor's `03_ui_followups/00_start.md` Q11, a): the two rules
  here, the review in this folder.
- The pin is a new `Sense.is_best` field (Q1); the review is pt first (Q2), by subagents (Q3);
  a one-letter lemma loses only its card (Q4).
- The code changes reach lang-tutor through one lang-tools release, lang-tutor's
  `03_ui_followups` phase 5.
- pt only for now (Q6). Drops are retractable, latest row wins (Q7). Senses the corpus lacks
  are added by the sibling folder `13_missing_senses` (Q8), which also brings back the lemmas
  whose only link was dropped.

## Phases

| #  | Phase                    | Plan                                             | Status  |
| -- | ------------------------ | ------------------------------------------------ | ------- |
| 1  | Build rules              | [`01_build_rules.md`](01_build_rules.md)         | done |
| 2  | Override input           | [`02_override_input.md`](02_override_input.md)   | done |
| 3  | Review harness           | [`03_review_harness.md`](03_review_harness.md)   | done    |
| 4  | Review run               | [`04_review_run.md`](04_review_run.md)           | done |
| 5  | Corrections              | [`05_corrections.md`](05_corrections.md)         | planned |

Status values: draft / planned / in progress / done / superseded / discarded.

## Log

Append-only. Newest at the bottom.

- 2026-11-03 : opened on branch `feat/12_card_senses` from lang-tutor's `03_ui_followups`
  phase 3 count (about 98 bad cards in the pt top 500); four phases, Q1 to Q4 raised.
- 2026-11-03 : Q1 to Q4 answered (a, b, a, a). Phases 2 to 4 planned; phase 1 started.
- 2026-11-03 : phase 1 done. One-letter lemmas are left out of card queries (in `_card_where`, not
  the derived table, which the cache would not refresh). Translations put a word before a symbol,
  and a single word before a phrase when the word is the more common (two simpler phrase rules
  measured and dropped: about a dozen regressions such as *negra* "blackamoor"). On the top 500
  of pt, es and fr: no one-letter card left, 91 first translations changed, about four arguably
  worse. `make check` green (407).
- 2026-11-04 : phase 2 done. `Sense.is_best` added (Parquet column, cache version 9), the
  curated `best_senses.jsonl` with its loader and applier (latest row per lemma, keyed on
  `concept_key`, stale counted), and the pin ordered first in the card pick and the sense list.
  No rebuild yet (no pins). The next transform run adds `is_best` to every row of the committed
  seed. `make check` green (412), docs build clean.
- 2026-11-04 : phase 3 reviewed before coding: `CardQuery.limit` stops at 500, so the worklist
  pages with `exclude_ids`; *homens* has no right sense (gold is every link wrong, not a pin);
  *bem* left out of the gold (its "rather" sense is real). Plan corrected in place.
- 2026-11-04 : phase 3 done. `ingestion.review_batches` (lock, append, rulebook hash, label
  error) shared with the look-alike review; `ingestion.sense_review` and `sense_review_cli`
  (worklist, import-gold, serve, apply, status); labels `k`, `pK`, `dK,L`, `x`, with `!`;
  every reviewed lemma gets a `BestSense` row, every drop a `FormDrop` of kind `wrong link`
  (`FormDrop.batch` and `BestSense.edge_case` added). Rulebook `docs/guides/sense_review.md`,
  skill `.claude/skills/sense-review/`, 7 gold lemmas in `data/curated/sense_review_gold.jsonl`.
  End-to-end test (serve, apply, rebuild); a dry run on the real corpus in a scratch folder
  served 200 cards in about 35k characters. Q5 raised. `make check` green (417).
- 2026-11-04 : Q5 answered a: the rare-homograph rule stands (`x`, the lemma leaves the corpus).
- 2026-11-04 : phase 4 started: pt worklist written (1,000 cards), 7 gold lemmas imported. Measured
  batch `s0001` by one subagent: 200 cards in 126 s and about 66k tokens, labels valid on the
  first apply, gold 2/2. 174 kept, 10 pinned, 16 senses and 12 lemmas dropped (verb forms and
  plurals, plus *alguma*, *inclusive*, *brasil* as edge cases), 12 edge cases. Not committed.
- 2026-11-05 : pt round done: `s0002` to `s0005` by four parallel subagents, each about 70k tokens
  and under two minutes, every apply valid on the first run. Over the 1,000 cards: 806 kept,
  102 pinned, 106 senses and 61 lemmas dropped, 64 edge cases, gold 9/9 (seven gold lemmas
  ran short for four parallel batches). Doubtful drops for a human look: *vinte* (only link the
  twenty-dollar bill), *mano* (only link a slur), *moderna*, *cura*, *campeonato*, *destaque*,
  *terras*, *brasil*, *pernambuco*. Missing senses noted: *sede* "headquarters", *sentido*
  "direction".
- 2026-11-05 : rebuilt (105 pins applied, 0 stale), gate PASS, seed gains `is_best` only.
  Re-listed the pt top 500: about 16 doubtful cards left (against about 98), most with no right
  sense in the corpus; listed in `04_review_run.md`. Not committed.
- 2026-11-05 : committed the rebuild (`3c54dea`), restarted the read API on 8010 (serves
  *tarde* "afternoon", no *seja*). Answers in `00_start.md`: es and fr not now (Q6), so phase 4
  closes on pt; drops become retractable (Q7), phase 5 planned; the missing senses go to a
  sibling folder (Q8). Raised Q9 (which drops to undo) and Q10 (the correction commands).
- 2026-11-05 : Q9 a (restore *moderna* only, re-pin *copa*), Q10 a (`restore` and `pin`
  commands) folded into `05_corrections.md`. The missing senses get folder 13,
  `13_missing_senses`, on `feat/13_missing_senses`.
- 2026-11-05 : correction to the line above: `13_missing_senses` is created on this branch
  (`feat/12_card_senses`), not on a branch of its own, at the user's choice.
