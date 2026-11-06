# Changelog

All notable changes to this project are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
