---
status: done
---

# Phase 1 - build rules

## Overview

Two deterministic fixes that need no review: one-letter lemmas stop being cards, and a card's
translations list a word before a symbol. Together about 26 of the 98 bad pt cards. Context:
[`00_start.md`](00_start.md); the letter rule removes only the card (Q4, a).

## Plan

- **One-letter lemmas:** the card query (`lemma_store._card_where`) leaves out a lemma of one
  character, so no `CardQuery` returns it; the lemma itself stays, and `lemma_card` still reads
  it by id (Q4, a). The filter sits in the query, not in the derived drill table, because the
  store cache is keyed on the Parquet signature and would not pick up a change to the table.
- **Translations:** `_card_translations` keeps "most frequent first" but moves a translation
  that is all digits, a Roman numeral or one letter after the words (pt *dez*: *ten*, then *x*,
  *10*). When every translation is a symbol, the order stays.
- Tests for both on the bootstrap seed or a small fixture; update the docstrings of
  `LemmaCard.translations` and the drill table, and `docs/library/` where it describes them.
- Re-list the top cards; both rules apply at query time, so no rebuild is needed.

## Done when

- No one-letter lemma in a card query; *dez*, *dois* and fr *tel* show a word first.
- `make check` passes.

## What the implementation found

- **Symbols alone were not enough.** pt *quatro* lists "4, Little Joe, four", so moving the
  symbol back put "Little Joe" first. A phrase now also moves after a single word, but only
  past one that is more common than the phrase (both read from `Sense.token_frequency`, the
  wordfreq Zipf of the surface form). Two simpler versions were measured on the top 500 of
  pt, es and fr and dropped:
  - every phrase after every single word: 167 first translations changed, about a dozen worse
    (pt *negra* "Black person" to *blackamoor*, es *cabello* "mane", fr *amoureuse*
    "infatuated", *contrairement* "contrarily");
  - the same with a floor of Zipf 3.0 on the single word: still fr *amoureuse* "infatuated",
    since the list also holds *potty* (3.3).
- **Result** on the 1,500 cards: no one-letter card is left (18 pt, 8 es, 9 fr before), and the
  first translation changes on 91: every digit and letter case (pt *dez* "ten", *dois* "two",
  fr *tel* "one", *sul* "south") and the phrase cases where a common word exists (*agora* "now",
  *trabalho* "job", es *noticias* "news", *iglesia* "church"). About four are arguably worse
  (*clara* "white" in pt and es, *fala* "delivery", fr *passe* "master"). "and so" stays ahead of
  *then*, since the phrase is the more frequent.
- The Roman-numeral match needs a digit in the same list, so a word such as *mix* is never
  taken for a numeral.
- Tests: `test_one_letter_lemma_is_never_a_card`,
  `test_translations_put_words_before_phrases_and_symbols`,
  `test_phrase_keeps_its_place_over_a_rare_word`. `make check` green (407 passed). Docs:
  `LemmaCard.translations`, `CardQuery`, `docs/library/lexicon.md`.
