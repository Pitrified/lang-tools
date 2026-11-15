---
status: planned
---

# Phase 3 - Card floor and card topics

## Overview

acerta's export needs two things from the card query: leave out rare lemmas (`00_start.md`
Q1, zipf 2.0) and say which topics each card has, so the app can filter on its side.
Context: [`00_start.md`](00_start.md).

## Goals

1. `CardQuery.min_zipf`, default `None` (no floor): a card is kept when its lemma's token
   frequency is at least the floor; a lemma with no frequency is left out once a floor is
   set.
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
