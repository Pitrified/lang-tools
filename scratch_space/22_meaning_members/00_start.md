---
status: done
priority: 0
description: |
  Clean the words of a meaning and their order: pt plurals and feminines stored beside their
  base, wrong pt members, translations led by an inflated -ing frequency, and the smaller
  checks the word page's dump shows. Reviewed curated rows, re-applied by the build.
comment: |
  Two open points of `scratch_space/open_points.md`, "Translations ranked by an inflated -ing
  frequency" and "Plural and wrong pt members of a meaning", both found from acerta's phone
  use and word page. Their entries moved here and came out of `open_points.md` on this
  branch, with "pt gloss equal to its word" (C8).
---

# Meaning members - start

## Original note

The user, on 2026-11-17, picking up the two open points raised by acerta (the "carreira -
calling - vocazione" card and the word page of *canal*): "Both in one folder", and "also list
from the big dump if we have other data quality checks to perform, propose list of checks to
fold in this folder".

The big dump is acerta's `assets/cards/pt_meanings.json`, written by its export from the 0.9.0
corpus: 29,926 meanings with their pt, en and it words and levels, the content of the word
page.

## Current state

Measured read-only on the 0.9.0 build and the dump, 2026-11-17. "Cards" are the pt drill cards
acerta draws from: single words, no form note, sense frequency 2.0 or more, 19,599 of them.

- **Translation order.** `LexiconStore._card_translations` orders a concept's words by
  `sense_frequency`, and `enrich` splits a lemma's wordfreq count over its senses only. An en
  noun with one noun sense (*calling*) keeps the whole surface count, verb uses included.
  353 cards lead with an en -ing form of an en verb, 250 of them with a non -ing word behind
  it. Many are right (*prédio - building*, *encontro - meeting*, *treino - training*), some
  are not (*existência - being*, *organismo - being*, *entrega - bringing*, *cartaz -
  posting*, *crescimento - growing*, *carreira - calling*). A rule that demotes -ing words
  would break the right ones.
  On *carreira* (concept `c__career-particular-occupation__433152e5e945`): *calling* 4.96
  (token 4.96, its only noun sense), *career* 4.88 (token 5.07 over three senses),
  *vocation* 3.08. WordNet puts all three in one concept, so *calling* is not a second
  meaning of *carreira*.
- **Inflected members.** A rule-made inflection gets a form note and is left out of the
  translations and the word page; a form the source lists as a word of its own has none.
  With the project's own `inflections.plural` and `feminine` rules:
  - 614 pt members are the plural of another member of the same meaning; 407 of them are
    also a card on that meaning (*alarmes*, *algas*, *acampamentos*, *aerossóis*), a second
    card for the same word. Some are plural-only words (*algemas*, handcuffs).
  - 349 are the feminine of another member; 201 are cards. A person noun is a word of its own
    (*amiga*, *afilhada*); an adjective's feminine is a form (*adoptada*, *arbitrária*).
- **Wrong members.** *cachimbo* (a smoking pipe) in canal's conduit meaning, *um* in "to a
  small degree" beside *um tanto*. No rule finds these. The card meanings with two or more
  pt words: 7,723 meanings, 28,822 entries; by the card's level A1 189, A2 277, B1 547,
  B2 1,296, C1 2,406, C2 3,008.
- **Existing tools.** `member_form_drops.jsonl` (`apply_form_drops`) removes a word's link to
  a concept; the card-sense review drops, pins and adds senses; `sense_additions` creates a
  missing link. All are curated JSONL, latest row wins, re-applied by the build.
- Subagent reviews cost about 1.2 session and 0.16 weekly plan points per batch of 100 items
  (21_unranked_pt_words).

## Proposed checks

Counts from the dump unless said otherwise. "In" means folded into this folder.

| # | Check | Count | Examples | Proposal |
| -- | ----- | ----- | -------- | -------- |
| C1 | pt plural stored beside its singular | 614 pairs, 407 cards | canais, alarmes, álcoois | in |
| C2 | pt feminine stored beside its masculine | 349 pairs, 201 cards | eterna, adoptada; amiga is fine | in |
| C3 | Card led by an -ing translation | 353 cards, 250 with an alternative | existência - being, carreira - calling | in |
| C4 | Wrong pt member of a meaning | no heuristic; 7,723 card meanings with 2+ pt words | cachimbo, um | in, all levels (Q3) |
| C5 | it cognate missing from the card's meaning | 1,350 same-part-of-speech cards | carriera, epoca, operare, restaurare | parked (Q4) |
| C6 | Capitalised pt member on a lower-case gloss | 109 | Aluminio, Bario, Argon, Aranhas, Beta | in |
| C7 | pt member of four or more words | 126 | por detraz ás avessas, exigente sobre seu traje | in |
| C8 | pt gloss equal to a member | 4, plus *jogar dados* (`c__dice__5277ff536fc6`), the quality gate's one "definition == lemma" failure | simultaneamente, reunir, vigiar | in (was the "pt gloss equal to its word" open point) |
| C9 | Accent-only variants in one meaning | 262 | académico / acadêmico, abdómen / abdômen | out: pt-PT and pt-BR spellings, both right |
| C10 | pt member spelled as an en or it member | 3,793 | dorsal, abdominal (cognates); aardvark, Abies | out: mostly true cognates and Latin names |
| C11 | Meaning with no pt gloss | 5,197 | | out: `19_pt_glosses` phase 3 |
| C12 | Meaning with no it word | 11,925 | | out: needs a source, not a review |
| C13 | Meaning with 12+ pt words | 3 | obscene terms for penis | out: they are right |

C6 and C7 overlap with C4 (a wrong member) and are found by rule, so they are cheap batches of
their own.

## Approach

- One review harness, the unranked review's shape (`review_batches`, `serve`, `apply` with
  validation, a rulebook hash on every row), with two batch kinds: a meaning's pt words
  (C1, C2, C4, C6, C7, the rule flags shown to the reviewer as hints) and a card's lead
  translation (C3).
- Fixes go through curated inputs, latest row wins:
  - a wrong, capitalised-duplicate or definition-like word: a drop in
    `member_form_drops.jsonl`;
  - a plural or adjective feminine: a new reviewed form row, which the build turns into a
    form note on that sense (Q1), so it leaves the cards and the meaning's word list like the
    rule-made inflections;
  - a wrong lead translation: a new reviewed lead row per concept and language, which the card
    translations put first (Q2);
  - the five pt glosses equal to their word (C8, with *jogar dados*): `gloss_overrides.jsonl`.
- A pilot of 500+ items, read by hand, before the full run; the full run goes in waves over
  several sessions, sized from the 21_unranked_pt_words cost and the usage read after the
  first wave.
- A rebuild, a release, and an acerta asset re-export at the end.

## Open questions

- Q1: What should happen to a plural or adjective feminine stored beside its base (C1, C2)?
  - a. Tag it as a form of the base, with a form note like the rule-made inflections: no
    card of its own, not listed among the meaning's words, still found as a form.
  - b. Drop its link to the meaning (member form drop): the word stays only if it has other
    meanings.
  - Recommended: a, because *alarmes* is a real word a learner meets, and a form note is how
    the corpus already treats *anos*; plural-only words (*algemas*) and person nouns (*amiga*)
    are kept as words by the review.
  - ANS: a.
- Q2: How should a wrong lead translation be fixed (C3)?
  - a. A reviewed preferred translation per card meaning, which `_card_translations` puts
    first; the review covers the 353 -ing cards.
  - b. A ranking rule that discounts an en -ing noun's share when an en verb has the same
    form, checked on 500+ cards.
  - Recommended: a, because the 353 cards hold right -ing leads (*building*, *meeting*) that
    any rule would demote.
  - ANS: a.
- Q3: How far should the wrong-member review (C4) go? It has no rule, so an agent reads every
  meaning in scope.
  - a. Card meanings at A1 to B2: 2,309 meanings, 7,140 words, about 23 batches, about 28
    session points.
  - b. All card meanings: 7,723 meanings, 28,822 words, about 77 batches, about 95 session
    points, more than one session.
  - c. Only the words C1, C2, C6 and C7 already flag.
  - Recommended: a, because the A1 to B2 words are the ones drills and word pages show most,
    and C1 and C2 can extend it later.
  - ANS: b. All card meanings, run over several sessions in waves.
- Q4: The it cognate the card lists but the meaning lacks (C5): 1,350 cards, some because the
  cognate means something else (*perversão* / *perversità*), some a real gap (*carreira* /
  *carriera*, *época* / *epoca*). Include it?
  - a. Yes: review the 1,350 and add the real gaps through `sense_additions`, about 14 batches.
  - b. Not now: park it as its own open point.
  - Recommended: b, because it adds words rather than cleaning them, and needs its own
    rulebook; this folder stays on noise.
  - ANS: b. Parked in `open_points.md` as "it cognate missing from the card's meaning".
- Q5: The meaning review only reads meanings with two pt words or more (7,743). The other 7,512
  card meanings have one pt word, the card itself, and a wrong one is a wrong card: the lead
  smoke batch showed *escotilha* (a ship's hatch) as the only word of "the production of young
  from an egg". Read those too?
  - a. Not in this folder: a card whose only meaning word is wrong is a wrong card sense, the
    card-sense review's question, which reviewed the most frequent cards; park the rest as an
    open point.
  - b. Yes: add them to the meaning worklist, about 75 more batches and 90 session points.
  - Recommended: a, because the question per card is "is this the card's meaning", which the
    card-sense review asks with the card's other senses in view, and this folder is already
    several sessions long.
  - ANS: a. Parked in `open_points.md` as "Card meanings with one pt word".
