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

### `lang_tools.lexicon`

The canonical content model plus the read/query helpers over the on-disk lemma
store. These read helpers are the in-process content surface phase 2 consumes
(phase 3 replaces them with HTTP calls).

- `Lemma` (thin token) and `LemmaExample`.
- `Concept` (language-independent synset) and `Sense` (the explicit
  lemma <-> concept edge hosting per-sense frequency / CEFR).
- `FalseFriendRelation`, `ConceptRelation` - decoupled relation edge tables.
- `lemma_id`, `concept_id`, `sense_id` - deterministic id constructors.
- `get_all_lemmas`, `get_lemma_by_id`, `get_lemmas_by_language`,
  `get_lemmas_by_topic`, `get_lemmas_filtered` - read/query helpers.

Importing `lang_tools.lexicon` loads the bootstrap content from disk (see the
content layout below).

### `lang_tools.llm` (content-producing chains)

The chains that *produce* content. Each exposes a typed input model, a typed
output model, and a `build_*_chain(chat_config, base_prompt_fol=...)` factory.

- `build_translation_chain` + `TranslationInput` / `TranslationOutput`.
- `build_conversation_chain` + `ConversationInput` / `ConversationOutput` /
  `ConversationTurn`.
- `build_paragraph_splitter_chain` + `SplitterInput` / `SplitterOutput`.
- `build_lemma_generator_chain` + `LemmaGeneratorInput` / `LemmaGeneratorOutput` /
  `GeneratedLemma`.
- `build_topic_suggestion_chain` + `TopicSuggestionInput` /
  `TopicSuggestionOutput`.
- `build_greeting_chain` + `GreetingInput` / `GreetingOutput`.

## Tutor-side concerns (extracted to `lang-tutor` in phase 2)

These were learner-facing / stateful and have been **moved out of `lang-tools`**
into `lang-tutor`. They are no longer importable from `lang_tools`; `lang-tutor`
owns them and depends on the frozen surface above for content.

- `lang_tutor.progress` - `UserLemmaProgress`, `compute_weight`, `select_lemmas`.
- `lang_tutor.exercises` - the five exercise mechanics.
- `lang_tutor.llm.tutor` - `build_tutor_chain` and the `TutorInput` /
  `TutorOutput` / `CorrectionBlock` / `ConversationBlock` / `ErrorDetail`
  models (the interactive feedback loop).
- `lang_tutor.webapp` - pages, runtime exercises API, OAuth, services.

## Content layout (git LFS)

Content lives at the repo root under `data/`, **read from the cloned working
tree** - never bundled into the wheel.

```text
data/
  bootstrap/
    en.csv  fr.csv  de.csv  es.csv  it.csv  pt.csv   # per-language lemma files
```

- **Lemmas**: one CSV per language under `data/bootstrap/`, loaded by
  `lang_tools.lexicon.lemma_store` via `LangToolsPaths.data_fol`.
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
