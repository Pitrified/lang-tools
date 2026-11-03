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

## Phases

| #  | Phase                    | Plan                                             | Status  |
| -- | ------------------------ | ------------------------------------------------ | ------- |
| 1  | Build rules              | [`01_build_rules.md`](01_build_rules.md)         | done |
| 2  | Override input           | [`02_override_input.md`](02_override_input.md)   | planned |
| 3  | Review harness           | [`03_review_harness.md`](03_review_harness.md)   | planned |
| 4  | Review run               | [`04_review_run.md`](04_review_run.md)           | planned |

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
