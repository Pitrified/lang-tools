# Frozen library API

This page is the **contract** that `lang-tutor` codes against. It fixes the
importable surface of `lang-tools` and the on-disk content layout *in place*
(still one repo, before any extraction). Phase 2 (the repo split) and phase 3
(the HTTP read API) both build on what is frozen here.

The freeze is a façade, not a behaviour change: the names below are promoted to
a stable public surface, and everything else is internal and may move when the
tutor concerns are extracted.

## Public surface `lang-tutor` may import

Three subpackages are frozen. Import the names from the subpackage `__init__`,
not from the module that happens to define them today.

### `lang_tools.language`

Shared language primitives, needed by both repos.

- `Language` - per-language configuration model.
- `LANGUAGE_PRESETS` - mapping of ISO 639-1 code to preset `Language`.
- `get_language` - lookup helper; raises `UnknownLanguageError` on miss.
- `UnknownLanguageError`.
- `normalize`, `has_accent`, `extract_accented_chars` - normalization helpers.

### `lang_tools.words`

The canonical content model plus the read/query helpers over the on-disk word
store. These read helpers are the in-process content surface phase 2 consumes
(phase 3 replaces them with HTTP calls).

- `Word` and supporting types `Gloss`, `GlossExample`, `WordExample`,
  `FalseFriend`, plus the `FrequencyLevel` literal.
- `word_id` - deterministic id for a `(text, language)` pair.
- `get_all_words`, `get_word_by_id`, `get_words_by_language`,
  `get_words_by_topic`, `get_words_filtered` - read/query helpers.

Importing `lang_tools.words` loads the bootstrap content from disk (see the
content layout below).

### `lang_tools.llm` (content-producing chains)

The chains that *produce* content. Each exposes a typed input model, a typed
output model, and a `build_*_chain(chat_config, base_prompt_fol=...)` factory.

- `build_translation_chain` + `TranslationInput` / `TranslationOutput`.
- `build_conversation_chain` + `ConversationInput` / `ConversationOutput` /
  `ConversationTurn`.
- `build_paragraph_splitter_chain` + `SplitterInput` / `SplitterOutput`.
- `build_word_generator_chain` + `WordGeneratorInput` / `WordGeneratorOutput` /
  `GeneratedWord`.
- `build_topic_suggestion_chain` + `TopicSuggestionInput` /
  `TopicSuggestionOutput`.
- `build_greeting_chain` + `GreetingInput` / `GreetingOutput`.

## Explicitly **not** frozen (tutor-side, moves in phase 2)

These are still importable today but are *not* part of the frozen contract.
They are learner-facing / stateful and migrate to `lang-tutor`. Only their
*dependencies* on the surface above need to stay stable.

- `lang_tools.progress` - `UserWordProgress`, `compute_weight`, `select_words`.
- `lang_tools.exercises` - the five exercise mechanics.
- `lang_tools.llm.tutor` - `build_tutor_chain` and the `TutorInput` /
  `TutorOutput` / `CorrectionBlock` / `ConversationBlock` / `ErrorDetail`
  models (the interactive feedback loop). Note: `lang_tools.llm` still
  re-exports these for now; treat them as tutor-side regardless.
- `lang_tools.webapp` - pages, runtime exercises API, OAuth, services.

## Content layout (git LFS)

Content lives at the repo root under `data/`, **read from the cloned working
tree** - never bundled into the wheel.

```text
data/
  bootstrap/
    en.csv  fr.csv  de.csv  es.csv  it.csv  pt.csv   # per-language word files
```

- **Words**: one CSV per language under `data/bootstrap/`, loaded by
  `lang_tools.words.word_store` via `LangToolsPaths.data_fol`.
- **Sentences / conversations**: currently *generated on the fly* by the
  conversation and splitter chains and **not** stored (per the design note,
  stored sentence content is out of scope for now). When promoted to stored
  content they land under `data/` (e.g. `data/sentences/<lang>.*`) and are
  covered by the same LFS glob without changing this contract.

### LFS tracking

`.gitattributes` tracks the whole content tree:

```gitattributes
data/** filter=lfs diff=lfs merge=lfs -text
```

Operators must `git lfs install` **before** cloning, or the working tree holds
pointer stubs instead of real content. The content is public, so no auth is
involved. This is the one-line operator setup that phase 3's HTTP service
depends on.

## Content is not in the wheel

The wheel packages only the code:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/lang_tools"]
```

`data/` sits at the repo root, outside `src/lang_tools/`, and is read from disk
at runtime through `LangToolsPaths.data_fol` (`root_fol / "data"`). So the
content is versioned repo data, never package-data: installing the wheel pulls
in no content, and the wheel stays small.
