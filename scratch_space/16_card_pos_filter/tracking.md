# implementation tracking

Let a card query leave out the function words that gained cards in v0.5.0, and give each pinned
lemma the part of speech of its card. Analysis and decisions in [`00_start.md`](00_start.md).

## Key decisions

- The filter lives in lang-tools; lang-tutor only sets it (user, 2026-11-10).

## Phases

| #  | Phase                    | Plan                                   | Status |
| -- | ------------------------ | -------------------------------------- | ------ |
| 1  | Part of speech of a card | [`01_card_pos.md`](01_card_pos.md)     | draft  |
| 2  | Function-word filter     | [`02_filter.md`](02_filter.md)         | draft  |
| 3  | Release v0.6.0           | [`03_release.md`](03_release.md)       | draft  |

Status values: draft / planned / in progress / done / superseded / discarded.

## Log

Append-only. Newest at the bottom.

- 2026-11-10 : bootstrapped after the v0.5.0 pin bump. Measured on the v0.5.0 corpus: 125 pt
  function-word lemmas; 90 of the 724 pinned pt lemmas have a part of speech other than their
  card's class (*um*, *uma*, *poder*, *dever* on curated concepts, 86 on WordNet ones).
  `CardQuery` filters on one class only. Q1 to Q4 raised.
