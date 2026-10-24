# Library overview

`lang_tools` owns the **content + data** layers of the language-learning
ecosystem: language primitives, the concept-centric lexicon with its build
pipeline and store, the content-producing LLM chains, and the content read
API. The learner-facing concerns (exercises, per-user progress, the tutor
chain, and the webapp) live in `lang-tutor`.

The [Frozen API](frozen_api.md) page records the public surface `lang-tutor`
imports and the git LFS content layout.

- [Frozen API](frozen_api.md) - the freeze contract: the importable surface
  and the content layout.
- [Language](language.md) - presets, normalisation, keyboard layouts.
- [Lexicon](lexicon.md) - the lemma / concept / sense model, relation edges,
  the store and drill cards, and the OMW build with its curated inputs.
- [LLM chains](llm.md) - content-producing structured chains for translation,
  conversation, topic suggestion, paragraph splitting, greetings, and lemma
  generation.
