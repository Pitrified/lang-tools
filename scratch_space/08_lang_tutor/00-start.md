# Splitting lang-tools into lang-tools + lang-tutor

## Original note

lang-tools is doing too much

- enumerate the functionalities
- try to split them into separate lang-tutor
- lang-tools does the ingestion of words and sentences cleanly, exposes them as
  a service, saves them in git lfs
- lang-tutor is doing the tutoring and the exercises

---

## Analysis

### Current state

`lang-tools` today is a single package that unifies five upstream apps
(`convo_craft`, `brazilian-bites`, `fala-comigo-ai-tutor`, `go-accenter`,
`worldly-words`). It currently spans the entire stack, from raw vocabulary
ingestion to a runnable exercise webapp.

### Functionality inventory (`src/lang_tools/`)

| Area | Modules | What it does |
| --- | --- | --- |
| **Language presets** | `language/` (`language.py`, `normalization.py`) | Language presets, normalization, keyboard/accent layouts. |
| **Word model + ingestion** | `words/` (`word.py`, `word_id.py`, `word_store.py`, `ingestion/` = wiktionary, csv, static_list, dedup) | Canonical `Word` model, stable ids, ingestion pipelines, dedup/merge, the word store. |
| **Progress + selection** | `progress/` (`progress.py`, `selection.py`) | `UserWordProgress`, `compute_weight`, weighted `select_words`. |
| **Exercises** | `exercises/` (sentence_reconstruction, pair_matching, diacritic_typing, wordle, conversational_tutor, base) | The five exercise mechanics + round/result protocol. |
| **LLM chains** | `llm/` (translation, conversation, tutor, topics, splitter, greeting, word_generator) | Structured `llm-core` chains for the 7 recurring LLM tasks. |
| **Webapp (pages)** | `webapp/routers/` (pages, exercises, words, progress, languages) | Jinja2/HTMX server-rendered UI. |
| **Webapp (runtime API)** | `webapp/api/v1/exercises_api.py`, `services/tutor_service.py`, `services/user_service.py` | JSON API that drives live exercise sessions; in-memory round + tutor-history state. |
| **Webapp (factory + auth)** | `webapp/main.py`, `webapp/core/` | `build_app()`, Google OAuth, dependencies. |
| **Shared infra** | `config/`, `params/`, `data_models/`, `metaclasses/` | Standard linux-box scaffolding (Params/Config, singletons, `BaseModelKwargs`). |

### Proposed split

The natural fault line is **data/content production vs. interactive practice**.

#### `lang-tools` (the content + data service)

Owns vocabulary and sentence *content*: produce it, store it, serve it.
Stateless with respect to any individual learner.

- `language/` - presets, normalization, keyboard layouts (shared vocabulary
  primitives).
- `words/` - `Word` model, ids, ingestion pipelines (wiktionary/csv/static),
  dedup/merge, word store.
- `llm/` content-generation chains that *produce* data: `translation`,
  `conversation`, `splitter`, `word_generator`, `topics`, `greeting`.
- **Persistence in git LFS**: ingested words and generated sentences/
  conversations serialized to versioned files, committed via LFS.
- **Service surface**: a read API (`GET /words`, filtered lookups, sentence/
  conversation fetch) that `lang-tutor` consumes. This is the "exposes them as
  a service" piece.

#### `lang-tutor` (the tutoring + exercise app)

Owns the *learner-facing* experience: stateful, per-user, interactive.

- `exercises/` - all five mechanics + round/result protocol.
- `progress/` - `UserWordProgress`, weighted selection (inherently per-user).
- `llm/tutor` chain + `tutor_service` (the live correction/conversation loop).
- `webapp/` - pages, the runtime exercises API, OAuth, user service, the
  in-memory (later DB-backed) session state.
- Consumes `lang-tools` as a dependency (and/or over its service API) to pull
  the word/sentence pool it drills the user on.

### Where the boundary gets blurry (decide explicitly)

1. **`Language` presets** - needed by both (normalization for ingestion,
   keyboard layouts for diacritic typing). Keep in `lang-tools` and re-export;
   `lang-tutor` depends on it.
2. **The `llm/` package is split down the middle.** Content-producing chains
   (translation, conversation, splitter, word_generator, topics, greeting) are
   data production -> `lang-tools`. The `tutor` chain is interactive feedback ->
   `lang-tutor`. `conversation` is debatable: generating a dialogue is content
   (lang-tools), but it's only ever consumed by the reconstruction exercise.
   Recommend: generation stays in `lang-tools`, the exercise that consumes it
   lives in `lang-tutor`.
3. **`progress/selection`** belongs to `lang-tutor`, but `select_words` needs
   the full word pool from `lang-tools`. Clean dependency direction
   (tutor -> tools), so this is fine.
4. **Sentences/conversations as first-class stored content.** Today
   conversations are generated on the fly. The note says lang-tools should
   "ingest sentences cleanly" and store in LFS - this implies promoting
   generated sentences/conversations to a persisted, versioned content type
   alongside `Word`, not just transient LLM output.

### Dependency direction

```
lang-tutor  ──depends on──▶  lang-tools  ──depends on──▶  llm-core, fastapi-tools
   (exercises, progress,        (words, sentences,
    tutor chain, webapp)         ingestion, content
                                 LLM chains, LFS store,
                                 read service API)
```

Strictly one-way: `lang-tools` must never import `lang-tutor`.

### Open questions / decisions needed

- **Coupling mode**: does `lang-tutor` import `lang-tools` as a Python package,
  call it over HTTP, or both (library for local, service for deployed)? The
  note's "exposes them as a service" leans toward an HTTP boundary, but a
  library dependency is far cheaper and can come first.
- **Git LFS as the store**: is LFS the durable store of record, or a publish/
  distribution format with another DB behind the live service? Sentences in
  LFS work well for versioned read-only content; per-user progress cannot live
  there (it's mutable, per-user -> DB in lang-tutor).
- **Webapp ownership**: confirmed entirely in `lang-tutor`? `lang-tools` then
  keeps only a thin read API (or no webapp at all, just a library + CLI).
- **Repo scaffolding**: new `lang-tutor` repo from `python-project-template`,
  reusing the same Params/Config/Singleton patterns; migrate
  `exercises/`, `progress/`, `webapp/`, `llm/tutor.py`, and the tutor service.

### Suggested next steps

1. Confirm the coupling mode (library vs. service vs. both) - drives everything.
2. Freeze the `lang-tools` public API (`Word`, sentence/conversation content
   models, the read/query functions) that `lang-tutor` will consume.
3. Define the LFS content layout (words file(s) + sentences/conversations
   file(s), per-language).
4. Scaffold `lang-tutor` and move `exercises/` + `progress/` first (no LLM
   dependency), validating the cross-repo import works.
5. Move the webapp + tutor chain last, once the data dependency is stable.
