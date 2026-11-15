# implementation tracking

Keep rare words out of drill cards with a commonness floor, re-cut the CEFR bands so C2 is
not the whole tail, and add a `medical` topic, so acerta can offer a topic picker with medical
words switchable. Analysis and decisions in [`00_start.md`](00_start.md).

## Key decisions

- The floor is a card query field, default off; the corpus keeps every word (Q1: zipf 2.0,
  set by acerta's export).
- `medical` is a new topic from a hypernym-root map in `data/curated/topics.json`, tagging
  every word the rule catches at any level; `health` stays (Q2).
- The bands are re-cut (Q3); phase 1 measures how before anything changes.
- A card carries its concept's topics, so an app can filter on its side.
- One corpus rebuild at the end, negotiated before it runs.

## Phases

| #  | Phase                     | Plan                                             | Status  |
| -- | ------------------------- | ------------------------------------------------ | ------- |
| 1  | Measure the band re-cut   | [`01_band_analysis.md`](01_band_analysis.md)     | in progress |
| 2  | Medical topic             | [`02_medical_topic.md`](02_medical_topic.md)     | planned |
| 3  | Card floor and topics     | [`03_card_floor.md`](03_card_floor.md)           | planned |
| 4  | Re-cut the bands          | [`04_band_recut.md`](04_band_recut.md)           | draft   |
| 5  | Rebuild and release       | [`05_rebuild.md`](05_rebuild.md)                 | planned |

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
