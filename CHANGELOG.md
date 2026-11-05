# Changelog

All notable changes to this project are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

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
