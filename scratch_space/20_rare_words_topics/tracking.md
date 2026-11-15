# implementation tracking

Keep rare words out of drill cards with a commonness floor, re-cut the CEFR bands so C2 is
not the whole tail, and add a `medical` topic, so acerta can offer a topic picker with medical
words switchable. Analysis and decisions in [`00_start.md`](00_start.md).

## Key decisions

- The floor is a card query field, default off; the corpus keeps every word (Q1: zipf 2.0,
  set by acerta's export).
- `medical` is a new topic from a hypernym-root map in `data/curated/topics.json`, tagging
  every word the rule catches at any level; `health` stays (Q2).
- The bands are re-cut (Q3) by raising the two upper edges for every language: C1 from 0.50,
  C2 from 0.60 (Q4).
- A card carries its concept's topics, so an app can filter on its side.
- One corpus rebuild at the end, negotiated before it runs.

## Phases

| #  | Phase                     | Plan                                             | Status  |
| -- | ------------------------- | ------------------------------------------------ | ------- |
| 1  | Measure the band re-cut   | [`01_band_analysis.md`](01_band_analysis.md)     | done |
| 2  | Medical topic             | [`02_medical_topic.md`](02_medical_topic.md)     | done |
| 3  | Card floor and topics     | [`03_card_floor.md`](03_card_floor.md)           | done |
| 4  | Re-cut the bands          | [`04_band_recut.md`](04_band_recut.md)           | done |
| 5  | Rebuild and release       | [`05_rebuild.md`](05_rebuild.md)                 | done |
| 6  | Health folded into medical | [`06_merge_health.md`](06_merge_health.md)      | done |

Status values: draft / planned / in progress / done / superseded / discarded.

## Log

Append-only. Newest at the bottom.

- 2026-11-15 : drafted from acerta's first phone use; Q1 to Q3 answered (floor zipf 2.0,
  medical on by default and removing every medical word when off, bands re-cut against the
  recommendation to keep them). Phases written. Review of the plans: `LemmaCard` carries no
  topics today and `CardQuery.topic` only includes one topic, so phase 3 adds the card's
  topics, a frozen-API addition that needs a tag; the rebuild is about 4 min plus a 30 s
  store load (`docs/guides/rebuild_corpus.md`) and replaces `data/lexicon/`, which the
  read API on port 8010 serves, so it restarts after; the band re-cut changes every
  consumer's levels, lang-tutor's included, which adapts after.
- 2026-11-15 : phase 1 run, read-only over the 2026-11-13 build after staging Kelly en and
  it (the user approved the download). Upper edges moved for all languages cost English 13
  points of exact agreement; rank quotas make pt worse; cutoffs fitted on Italian Kelly fix
  Italian's +1.06 offset (38.3% exact, 78.9% within one, offset 0) and, used for pt, bring
  acerta's floored C2 from 79% to 41%. Unknown frequencies score as mid-scale, which puts
  voluto at C1. Asked as `00_start.md` Q4 and Q5.
- 2026-11-15 : phase 1 done. Q4 answered a: C1 from 0.50 and C2 from 0.60 for every language
  (the recommendation was per-language cutoffs); phase 4 written in full. Q5 not taken:
  unknown frequencies and stray non-pt words (voluto is Italian, from `omw`) parked as two
  open points, to be categorized by agents later.
- 2026-11-15 : phases 2 to 4 done, in one commit because their docs share
  `docs/library/lexicon.md`. Two sonnet subagents wrote phases 2 and 3 in parallel; phase 4
  (the two upper cutoffs, their comment and the CEFR doc) by hand. Review: the floor was on
  the lemma's token frequency and is now on the card's `sense_frequency`, the value the
  user's 2.0 was measured on (the plans said "lemma" wrongly, corrected). `make check`
  passes, 571 tests. The user approved the rebuild ahead.
- 2026-11-15 : phase 5 done: rebuilt (counts identical; B2 88,532, C1 183,949, C2 249,782;
  2,744 medical concepts), seed refreshed, `make check` passes; the quality gate's one
  failure ("jogar dados", an llm pt gloss equal to its word) predates this folder and is an
  open point. 0.8.0 and its changelog written; the tag waits for the merge. The read API on
  8010 restarted. Close review: the floor and topics behave on the store as measured; the
  acerta export moves to acerta phase 9. All five phases done.
- 2026-11-15 : phase 6, asked by the user from acerta's settings screen: `health` folded
  into `medical` (OMW's `medicine` domain maps to it; the vocabulary is 26 topics). The
  user agreed the second rebuild: counts unchanged, 2,817 medical concepts, none health.
  `make check` passes; the API restarted. Folder done again.
