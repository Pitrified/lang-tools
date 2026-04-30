# Library overview

`lang_tools` is organised around five orthogonal layers. Each one is
documented in its own page below.

- [Language](language.md) - presets, normalisation, keyboard layouts.
- [Words](words.md) - the canonical `Word` model and ingestion pipelines
  (Wiktionary, CSV, static lists).
- [Progress](progress.md) - per-user progress tracking and weighted
  selection.
- [Exercises](exercises.md) - the five shared exercise mechanics.
- [LLM chains](llm.md) - structured chains for translation, conversation,
  tutoring, topic suggestion, paragraph splitting, greetings, and word
  generation.

The implementation follows the plan documents under
`scratch_space/vibes/10-language-overview/` (00 through 06, excluding the
unified webapp).
