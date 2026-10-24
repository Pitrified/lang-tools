# Changelog

All notable changes to this project are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

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
