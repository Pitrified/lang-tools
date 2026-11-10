---
status: draft
priority: 0
description: |
  Let a card query leave out the function words (pronouns, articles, prepositions,
  conjunctions), which have had cards since v0.5.0, and give each lemma the part of speech of its
  card, so the filter catches *um* and *uma*.
comment: |
  Raised on 2026-11-10 after the v0.5.0 pin bump in lang-tutor. The filter lives in lang-tools
  (user's call); lang-tutor only sets it.
---

# Function-word filter for cards

## Origin

`14_number_modal_words` phase 7 gave the 128 closed-class words of the pt top 1,000 a card on a
curated concept (pt *eu* "I", *de* "of, from"), with a function-word part of speech, and left
choosing which of them to drill to lang-tutor
(`14_number_modal_words/00_start.md` Q13).
Since lang-tutor pinned v0.5.0, its drills can draw them: it samples a random window of cards
weighted by CEFR level, with no filter on part of speech.
User, 2026-11-10: the filter is done on the lang-tools side; *um* and *uma*, which are still a
noun and an adverb, are fixed.

## Current state

- `CardQuery.part_of_speech` keeps one class (`d.part_of_speech = ?` in
  `lemma_store._card_where`); nothing excludes a class.
- lang-tutor builds four queries (`webapp/api/v1/exercises_api.py`): pair matching, wordle,
  diacritic typing, sentence reconstruction. None sets `part_of_speech`.
- pt lemmas by part of speech: 35,958 noun, 4,815 adjective, 4,016 verb, 1,280 adverb,
  53 determiner, 36 preposition, 23 pronoun, 13 conjunction. en has 67 function-word lemmas
  (the members of the curated concepts); es, fr and it none, since their closed-class words are
  dropped without a card.
- A lemma has one part of speech, taken from its first WordNet sense, whatever its card shows.
  Of the 724 pt lemmas with a pinned card, 90 have a part of speech that differs from the class
  of their pinned concept (`LEXFILE_POS` of its lexfile):
  - 4 on curated concepts: *um* noun and *uma* adverb (card "a, an", determiner), *poder* and
    *dever* noun (card "can" / "must", verb);
  - 86 on WordNet concepts, mostly noun for an adjective card (48: *escolar*, *clara*,
    *brancos*), noun or adjective for a verb card (25: *era*, *fala*, *são*, *visto*), and
    *hoje*, *lá*, *mal* noun for an adverb card.
  Unpinned lemmas were not measured: their card is chosen by sense frequency, so the same
  mismatch is possible there too.

## Open questions

- Q1: The shape of the filter on `CardQuery`.
  - a. `function_words: Literal["include", "exclude", "only"]`, with the classes defined once in
    lang-tools (`pronoun`, `determiner`, `preposition`, `conjunction`); `only` serves a later
    function-word drill.
  - b. `exclude_part_of_speech: list[str]`, generic; each client lists the classes.
  - c. `content_words_only: bool`.
  - Recommended: a, because lang-tools then owns which classes count as function words, and a
    client sets one value.
  - ANS: b (user, 2026-11-10).
- Q2: The default of the filter.
  - a. Exclude by default: every drill of lang-tutor gets it with no change there, and a client
    that wants the function words asks for them.
  - b. Include by default (today's behaviour): lang-tutor sets `exclude` on its four queries.
  - Recommended: a, because no current drill wants them, and the frozen surface change is one
    CHANGELOG line; `lemma_card` by id is not affected.
  - ANS: a (user, 2026-11-10). With Q1 b the default of `exclude_part_of_speech` is the
    four function-word classes; see Q5 for how a client asks for them over HTTP.
- Q3: Which lemmas take the part of speech of their card.
  - a. Every lemma with a pinned card takes its pinned concept's class: the 90 pt lemmas above.
  - b. Only pins on curated concepts: *um*, *uma*, *poder*, *dever*.
  - c. A curated per-lemma override, written by hand for *um* and *uma*.
  - Recommended: a, because the card is what a filter acts on, and a deterministic rule covers
    the 86 WordNet cases too; the 90 are read before and after. The part of speech also feeds
    the look-alike matching (`lookalikes.cognate_key` treats a verb apart), so phase 1 counts the
    look-alike edges before and after.
  - ANS: a (user, 2026-11-10).
- Q4: Unpinned lemmas, whose card is the most frequent sense.
  - a. Out of scope: measure the mismatch only, and note it.
  - b. Same rule for the card sense of every lemma.
  - Recommended: a, because the frequency-chosen card is less reliable than a pin, and the
    filter needs only the function words, which are all pinned or created with their class.
  - ANS: a, and assess it (user, 2026-11-10): phase 1 measures the unpinned mismatch and
    reports it.
- Q5: How a client asks for function words over HTTP. With Q1 b and Q2 a,
  `exclude_part_of_speech` defaults to the four function-word classes, and a query string cannot
  send an empty list: leaving the key out gives the default.
  - a. A class named in `part_of_speech` is never excluded, so `part_of_speech=pronoun` returns
    pronouns; a mixed pool (content and function words) is not possible over HTTP.
  - b. An empty value means exclude nothing: `?exclude_part_of_speech=` gives `[""]`, which a
    validator turns into `[]`.
  - c. Both: a for a query of one class, b for a mixed pool.
  - Recommended: c, because without a a query for pronouns silently returns nothing, and b is
    the only way to a mixed pool; each is one line.
  - ANS: b (user, 2026-11-10). A query for one function class sends both keys:
    `?part_of_speech=pronoun&exclude_part_of_speech=`; the docs say so.
