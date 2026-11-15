---
status: done
---

# Phase 3 - Card floor and card topics

## Overview

acerta's export needs two things from the card query: leave out rare lemmas (`00_start.md`
Q1, zipf 2.0) and say which topics each card has, so the app can filter on its side.
Context: [`00_start.md`](00_start.md).

## Goals

1. `CardQuery.min_zipf`, default `None` (no floor): a card is kept when its best-sense
   frequency (`sense_frequency`, which the measurements of `00_start.md` used) is at least
   the floor; a card with no frequency is left out once a floor is set.
2. `LemmaCard.topics`: the topics of the card's concept (the best sense's), sorted.
3. The read API takes `min_zipf` as a query parameter and returns `topics`.

## Plan

- `card.py`, the card table query and the hydration; the webapp's card routes.
- Tests: the floor on the seed (a rare lemma out, a common one in, no floor keeps both);
  topics on a card; the API round trip.
- `docs/library/frozen_api.md`: both additions, since the version they ship in; a new tag
  at the end of the folder.
- `docs/library/lexicon.md`, the card query section.

## Out of scope

- An "exclude topics" query filter: acerta filters on its side, no caller needs it yet.

## Done when

- `make check` passes.

## What the implementation found

- A sonnet subagent first put the floor on the lemma's token frequency, the wording this
  plan had. acerta's `freq`, which every measurement and the user's 2.0 used, is the card's
  `sense_frequency`; the review moved the floor there. `lemma_drill` already carries it, so
  the store's cache version and table shape did not change.
- The read API needed no router change: `CardQuery` is bound with `Query()`, so
  `min_zipf` is a query parameter and `topics` serializes with the card.
- `docs/library/frozen_api.md` names the additions "since the next tag after v0.7.0",
  replaced by the tag in phase 5.
