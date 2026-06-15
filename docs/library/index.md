# Library overview

`lang_tools` owns the **content + data** layers of the language-learning
ecosystem: language primitives, the canonical `Lemma` model with ingestion, and
the content-producing LLM chains. The learner-facing concerns (exercises,
per-user progress, the tutor chain, and the webapp) were extracted to
`lang-tutor` in phase 2 of the split; see
`scratch_space/08_lang_tutor/` for the migration plan.

The [Frozen API](frozen_api.md) page records the public surface `lang-tutor`
imports and the git LFS content layout.

- [Frozen API](frozen_api.md) - the freeze contract: the importable surface
  and the content layout.
- [Language](language.md) - presets, normalisation, keyboard layouts.
- [Lexicon](lexicon.md) - the canonical `Lemma` model and ingestion pipelines
  (Wiktionary, CSV, static lists).
- [LLM chains](llm.md) - content-producing structured chains for translation,
  conversation, topic suggestion, paragraph splitting, greetings, and lemma
  generation.
