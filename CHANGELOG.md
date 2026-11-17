# Changelog

All notable changes to this project are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.10.1] - 2026-11-17

### Data

- pt *canal*'s conduit meaning reviewed (meaning review batch `w9003`): *cachimbo* (a smoking
  pipe) and *chaminés de fábrica* leave it, *canais* becomes a form of *canal*. Corpus rebuilt:
  lemmas 341,144 to 341,143, senses 576,733 to 576,731.

---

## [0.10.0] - 2026-11-17

The words of a card's meaning were reviewed by Claude subagents under a written rulebook, for
1,705 of the 7,743 card meanings with two pt words or more: a plural or an adjective's feminine
stored as a word of its own becomes a form of its base, a word naming something else, a
definition or a misspelled or pre-1990 duplicate leaves the meaning. The 207 card meanings led
by an en -ing verb form were reviewed too, and 84 get a reviewed first word (*carreira* -
*career*, not *calling*). Ten pt glosses that repeated their word were rewritten.

### Added

- `Sense.is_lead` (default `False`): a reviewed lead translation, which a card's translations
  put first. The leads come from the curated `data/curated/lead_translations.jsonl`
  (`ingestion.lead_translations`), keyed on concept and language; `_build.json` records them
  under `lead_translations`. The store cache moves to version 11.
- `ingestion.meaning_review` and its command line `meaning_review_cli` (worklist, `serve`,
  `apply`, `status`), the rulebook `docs/guides/meaning_review.md` and the `meaning-review`
  skill. Meaning batches label each pt word of a card's meaning as kept, a form of another word
  (a `sense_additions.jsonl` row with its form note) or dropped (a `member_form_drops.jsonl`
  row, kind `meaning`); lead batches pick the first en word of a meaning led by an -ing verb
  form (a `lead_translations.jsonl` row). Every label is logged in
  `data/curated/meaning_review_log.jsonl`.

### Fixed

- A store built from a corpus that predates a column (`Sense.is_lead`) read NULL for it and
  failed on the model; a null where the field's default is not null now takes the default
  (`codec.model_from_row`).

### Data

- `data/curated/meaning_review_log.jsonl`: the latest labels of 4,759 words over 1,705
  meanings, 4,319 kept, 136 forms, 304 dropped. Its rows in `member_form_drops.jsonl` (kind
  `meaning`, 421 drops and 25 restores from the re-checks), `sense_additions.jsonl` (143 forms,
  2 retracted) and `lead_translations.jsonl` (84 leads).
- Ten pt gloss overrides in `gloss_overrides.jsonl`, for the glosses equal to their word; the
  quality gate's "definition == lemma" invariant passes again.
- Corpus rebuilt: lemmas 341,353 to 341,144, senses 577,087 to 576,733; pt words stored as the
  plural of another word of the same meaning 614 to 508, as its feminine 349 to 316.

---

## [0.9.0] - 2026-11-15

The 4,814 single pt words wordfreq has no count for were reviewed by Claude subagents under a
written rulebook: the real ones get a commonness that places their band, the misspelled, foreign
and malformed ones leave the corpus.

### Added

- `ingestion.unranked_review` and its command line `unranked_review_cli` (worklist, `serve`,
  `apply`, `recheck`, `status`), the rulebook `docs/guides/unranked_review.md` and the
  `unranked-review` skill. Labels: common, uncommon, rare, misspelled (with the right spelling),
  not Portuguese (with the language), malformed.
- `data/curated/commonness_buckets.jsonl` (4,045 words) and `unranked_review_log.jsonl`
  (every label, with the rulebook hash).
- The build stage `with_bucket_zipf`: a bucketed word with no wordfreq count gets a stand-in
  frequency before the bands (common 3.5, uncommon 2.5, rare 1.5); a real count wins.
  `_build.json` records it under `commonness_buckets`.

### Removed

- 769 pt words (423 misspelled, 227 not Portuguese, 119 malformed), through 813 rows of
  `member_form_drops.jsonl` with kind `unranked`, one per concept link. pt goes from 63,692 to 62,923 lemmas; pt
  words with no frequency from 8,597 to 3,783, all of them multiword.

## [0.8.0] - 2026-11-15

Drill cards can leave out rare words and say which topics they belong to, a `medical` topic
catches diseases, symptoms, drugs and treatments, and C2 no longer holds every word past the
most frequent few thousand.

### Added

- `CardQuery.min_zipf` (default `None`): keep only cards whose `sense_frequency` is at least the
  floor; a card with no frequency is left out once a floor is set. A query parameter of the read
  API too.
- `LemmaCard.topics`: the best concept's topics, sorted.
- The topic `medical`, from two new maps in `data/curated/topics.json`: `hypernym` (14 root
  concepts whose taxonomy descendants are tagged) and `gloss_tag` (an English gloss opening with
  a field tag such as `(pathology)`). The 2026-11-15 build tags 2,817 concepts, OMW's `medicine` domain included; `_build.json`
  records the concepts per root and the roots the build lacks under `topics`.

### Removed

- The topic `health`: OMW's `medicine` domain, its only source, now maps to `medical`, so one
  topic holds every medical word.

### Changed

- The two upper CEFR cutoffs are set, not fitted: C1 starts at score 0.50 and C2 at 0.60, for
  every language. On the 2026-11-15 build B2 holds 88,532 senses (was 30,001), C1 183,949 (was
  34,140) and C2 249,782 (was 458,122); A1 to B1 are unchanged. Against Kelly, English agreement
  is 29.1% exact / 72.7% within one band (was 42.1% / 74.0%), Italian 33.1% / 76.1% (was 22.9% /
  63.7%).

## [0.7.0] - 2026-11-11

The frequent pt inflected forms get a lemma by rule, on their base word's meaning, and stay out of
drills and word lists unless asked for.

### Added

- `ingestion.inflections`: pt inflection rules of our own, with no third-party morphology table. They
  generate a noun's plural, an adjective's feminine and plurals, the feminine of a noun naming a
  person, and a verb's finite forms, personal infinitive, gerund and past participles (regular
  paradigms with spelling and stem changes, and a table of 28 irregular verbs and their
  compounds). A form several bases give gets one base, and a form note written from its tags
  (`3rd person singular preterite of "ser"`, `plural of "ano"`).
- The build stage `apply_inflections`, right after the sense additions: each pt form of
  `wordfreq` zipf 3.0 and up that the build lacks gets a lemma with its base's senses of the form's
  class, and takes its base's pinned sense (`propagate_base_pins`), so its card is its base's card.
  The 2026-11 build adds 12,395 pt forms with 49,675 senses; `_build.json` records them under
  `inflections`. The rows carry the new provenance tag `inflection`. A reviewed form row still wins.
- `CardQuery.include_forms` (default `False`): keep the inflected forms, the cards with a
  `form_note`.

### Changed

- A card query leaves out the inflected forms by default, the reviewed ones (pt *anos*, *foi*)
  included; `lemma_card` by id still reads a form's card.
- A sense with a form note is never a card translation or own-language synonym, a
  `require_translation` match, a `lemmas_for_concept` member, or a lemma of a hydrated concept:
  the en card "year" listed pt *anos* before *ano*, and "be" listed 26 pt words. `senses_for_concept`
  keeps every edge.
- The card-sense review worklist leaves the inflected forms out.
- The bootstrap seed has 276 inflected forms (863 lemmas, 1,000 senses).

---

## [0.6.0] - 2026-11-10

Card queries leave out the function words unless a client asks for them.

### Added

- `CardQuery.exclude_part_of_speech`: the lemma parts of speech a card query leaves out. Its
  default is `card.FUNCTION_WORD_POS` (pronoun, determiner, preposition, conjunction); an empty
  list, or `?exclude_part_of_speech=` over HTTP, keeps every class. A query for one function-word
  class sets both fields (`?part_of_speech=pronoun&exclude_part_of_speech=`). A lemma with no part
  of speech is kept.

### Changed

- A card query no longer returns the function words by default (pt *eu*, *um*, *de*, *mas*);
  `lemma_card` by id is not affected, and the card-sense review worklist still serves them.
- A lemma with a pinned card takes the part of speech of that card
  (`best_senses.apply_pinned_part_of_speech`): pt *um* and *uma* are determiners, *poder* and
  *dever* verbs, 90 pt lemmas in all. `_build.json` records the count under `best_senses`.
- The bootstrap seed: pt *preciso* is a verb.

---

## [0.5.0] - 2026-11-10

The pt corpus gains its number words, its modal verbs, the forms and function words of its 1,000
most frequent words, and the modern spelling.

### Added

- Reviewed concept additions, `data/curated/concept_additions.jsonl`, applied at build by
  `ingestion.concept_additions`: a concept WordNet lacks, with its English gloss and members,
  keyed on a manual source key; the latest row of a key wins, and `add: false` retracts one.
  `_build.json` records what they applied and how many rows were stale.
- Curated concepts for the modal verbs (*poder* "can", *dever* "must") and for the function
  words: pronouns, articles, possessives, demonstratives, quantifiers, prepositions and
  conjunctions (pt *eu* "I", *o* "the", *de* "of, from").
- `ingestion.spelling_reform.respell_pt`: the pre-2009 pt spellings of the pt wordnet
  (*idéia*, *seqüência*, *vôo*) are respelt at build, folding into the modern word when both
  exist.
- pt data: the missing cardinal numbers, content words of the top 5,000, the frequent forms of
  the top 1,000 with their form notes, and cards for the 128 closed-class words of the top
  1,000.

### Changed

- A created lemma takes its part of speech from one shared map of lexfile classes,
  `sense_additions.LEXFILE_POS`, which also knows `pronoun`, `determiner`, `preposition` and
  `conjunction`.
- The closed-class list: 20 pt function words added, *uma* and *consigo* removed, since they
  are also "one" and "I manage".
- The rulebook `docs/guides/sense_review.md`: a closed-class word takes a curated concept, and
  only a WordNet concept is refused.

---

## [0.4.0] - 2026-11-06

Drill cards gain the everyday meanings the corpus did not link, and verb forms and plurals say
which form they are.

### Added

- `Sense.form_note` and `LemmaCard.form_note`: which form of its base word a card is, for an
  inflected form linked to the base word's concept (pt *são*: `3rd person plural present of
  "ser": they are`).
- `LexiconStore.get_concept_by_key`, a concept looked up by its slug-free key.
- Reviewed sense additions, `data/curated/sense_additions.jsonl`, applied at build: a link to a
  concept the word lacked, creating the lemma when the corpus does not hold it; the latest row
  of a lemma and concept wins, and `add: false` retracts one.
- The card-sense review: the `a` action (add a meaning), `REMOVED` items (a word an earlier
  review took out, served to bring back), `recheck` of listed words, a blind second review
  (`--shadow`, which writes no curated row) and `agreement` between two reviews, counting
  WordNet twins apart; the commands `worklist-removed`, `concepts` (with commonness, most
  common first), `add` and `drop`. The how-to `docs/guides/missing_senses.md`.

### Changed

- The rulebook `docs/guides/sense_review.md`: `k` is the everyday meaning itself, a near miss is
  not the card, the frequent reading wins over an everyday homograph, an inflected form links to
  its base word with a form note, twins take the concept holding the base word, and proper
  nouns are capitalised.
- A review label always pins the card it leads to, so a `k` on a re-check keeps an earlier pin.
- The sense gold is latest-row-wins per lemma, and an imported gold answer writes the addition
  it needs.
- The look-alike `recheck` also serves gold pairs, and a disputed gold pair leaves the gold
  pool.
- The card cache version is 10.
- Curated data: the review of the 1,000 most frequent pt cards under the new rules (197 senses
  added, 63 lemmas created, 300 pins), look-alike recheck `r0011`, and pt glosses for the
  concepts the additions linked.

## [0.3.0] - 2026-11-05

Drill cards teach the right meaning of the most frequent pt words.

### Added

- `Sense.is_best` (default `False`): a reviewed best-sense pin, which the card's best-sense pick
  takes first. The pins come from the curated `data/curated/best_senses.jsonl`.
- The card-sense review: `lang_tools.lexicon.ingestion.sense_review` and its command line
  `sense_review_cli` (`worklist`, `import-gold`, `serve`, `apply`, `status`, and the hand
  corrections `restore` and `pin`), the rulebook `docs/guides/sense_review.md` and the
  `sense-review` skill.
- `lang_tools.lexicon.ingestion.review_batches`: the work-folder lock, row append and rulebook
  hash shared by the look-alike and card-sense reviews.

### Changed

- A one-letter lemma is no longer a drill card (`lemma_card` still reads it by id).
- Card translations put a word before a digit, a single letter or a Roman numeral, and a single
  word before a rarer phrase (pt *dez* shows "ten", not "x").
- `member_form_drops.jsonl`: only the latest row of a sense counts, so a later `drop: false` row
  retracts a drop.
- `lang_tools.lexicon` imports without the `webapp` extra: `LangToolsParams.webapp` loads on
  first use.
- Curated data: the look-alike review of tiers A and B (pt against en and it), and the
  card-sense review of the 1,000 most frequent pt cards.

## [0.2.0] - 2026-10-24

First tagged release, for `lang-tutor` to pin.

### Added

- `lang_tools.lexicon`: the concept-centric model (`Lemma`, `Concept`, `Sense`, relation edges
  including `LookalikeRelation` for false friends and cognates), the Parquet corpus behind
  `LexiconStore`, the quality gate, and `LemmaCard` / `CardQuery` drill cards.
- `lang_tools.lexicon.ingestion`: the reproducible `build_initial` from Open Multilingual Wordnet
  for en, pt, es, fr and it, re-applying the curated inputs under `data/curated/`, and the
  look-alike candidate generator and review CLI.
- `lang_tools.llm`: the maintenance chains and the checkpointed `runner`.
- `Makefile` from the template, with `dev-llm-core` and `dev-fastapi-tools`.

### Changed

- The read API (`lang_tools.webapp`) serves lemmas, concepts and cards instead of words.
- The `word_generator` chain is now `lemma_generator`.

### Removed

- `lang_tools.words`: the `Word` model, the word store and the Wiktionary loader, replaced by
  `lang_tools.lexicon`.
