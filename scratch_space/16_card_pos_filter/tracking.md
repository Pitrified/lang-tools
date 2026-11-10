# implementation tracking

Let a card query leave out the function words that gained cards in v0.5.0, and give each pinned
lemma the part of speech of its card. Analysis and decisions in [`00_start.md`](00_start.md).

## Key decisions

- The filter lives in lang-tools; lang-tutor only sets it (user, 2026-11-10).
- A generic `CardQuery.exclude_part_of_speech` list (Q1 b), defaulting to the four function-word
  classes (Q2 a); an empty value (`?exclude_part_of_speech=`) turns it off (Q5 b).
- Every pinned lemma takes its card's class (Q3 a); unpinned lemmas are assessed, not changed
  (Q4 a).

## Phases

| #  | Phase                    | Plan                                   | Status |
| -- | ------------------------ | -------------------------------------- | ------ |
| 1  | Part of speech of a card | [`01_card_pos.md`](01_card_pos.md)     | done   |
| 2  | Function-word filter     | [`02_filter.md`](02_filter.md)         | draft  |
| 3  | Release v0.6.0           | [`03_release.md`](03_release.md)       | draft  |

Status values: draft / planned / in progress / done / superseded / discarded.

## Log

Append-only. Newest at the bottom.

- 2026-11-10 : bootstrapped after the v0.5.0 pin bump. Measured on the v0.5.0 corpus: 125 pt
  function-word lemmas; 90 of the 724 pinned pt lemmas have a part of speech other than their
  card's class (*um*, *uma*, *poder*, *dever* on curated concepts, 86 on WordNet ones).
  `CardQuery` filters on one class only. Q1 to Q4 raised.
- 2026-11-10 : Q1 to Q4 answered (b, a, a, a with an assessment) and folded in; Q5 raised (an
  empty list cannot be sent in a query string).
- 2026-11-10 : Q5 answered b (an empty value turns the exclusion off) and folded in.
- 2026-11-10 : phase 1 done. Review corrected two claims (look-alike edges cannot move in the
  build; class is the synset majority). `apply_pinned_part_of_speech` after the pins: 90 pt
  lemmas changed, all read right on 8010, other counts unchanged. Q4 assessed: 440 of 45,470
  unpinned pt lemmas (about 1%) differ from their card's class, 26 in the top 1,000; left.
  `make check` 470, gate PASS, docs build.
