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
   ANS: was a typo. in kaikki data words are called "senses", so an idiomatic short group of words is grouped in a single entity. irrelevant noise for now, not an issue.

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

ANS: these three decisions are interrelated
Main question: git LFS content accessibility across the repo boundary

if we use the pattern of
` "fastapi-tools @ git+https://github.com/Pitrified/fastapi-tools@v0.1.0",`
to pull in `lang-tools` as a library dependency,
is the git LFS content (words + sentences) accessible to `lang-tutor` as part of that dependency?
could the LFS content be pulled down the first time a consume uses `lang-tools`?

the other pattern is a service API, not a dependency, so the question is irrelevant: who pulls the LFS content is the human user of the service, who will need to git clone the repo and spin up the service locally or deploy it somewhere.
then `lang-tools` will also be a dependency of `lang-tutor` but just to have the shared data models and LLM chains, not the content itself which will be via HTTP.

#### Findings: does `pip install git+https@tag` deliver the LFS content?

Short answer: **not reliably, and never lazily.** Treat LFS content as
something delivered out-of-band, not smuggled through a pip dependency.

Mechanics, in order:

1. **pip does a real `git clone`** of the repo into a temp dir for
   `git+https://...@tag`, then builds a wheel/sdist from that checkout. This is
   a true clone, not a GitHub archive/tarball. (Archives -
   `.../archive/<tag>.tar.gz` and sdists - contain only the LFS *pointer*
   stub files, never the real blobs, so an archive-based install can never
   carry LFS content.)
2. **The clone only resolves LFS if `git-lfs` is installed on the consumer's
   machine** and registered as a git filter (`git lfs install`, which sets the
   global smudge/clean filters). If git-lfs is present, checkout runs the
   smudge filter and pulls real content; if it is absent, the working tree -
   and therefore the wheel built from it - contains pointer stubs (a few lines
   of text), and the data is silently broken.
3. **Even with smudge working, the data files must be declared as package data**
   (e.g. under `src/lang_tools/`, included via `tool.hatch`/`setuptools`
   package-data) or the build drops them from the wheel. That bundles the full
   content into every install and bloats the wheel.
4. **No lazy "fetch on first use" from pip.** pip resolves everything at install
   time. "Pull the LFS content the first time a consumer uses `lang-tools`"
   is not something pip does - it would require explicit runtime code in
   `lang-tools` (download from the LFS endpoint / a GitHub release asset / a
   CDN, cached under `cache_fol`).

Conclusion: a library dependency that *carries* the content is fragile
(depends on the consumer having git-lfs), bloats the wheel, and gives no
laziness. So decouple **code** from **content**:

- `lang-tools` as a **library dependency** ships only code: shared data models,
  `Word`, the read/query helpers, and the LLM chains. No bundled content.
- The **content** (words + sentences) is delivered via the **service API (A)**:
  the human runs/deploys `lang-tools`, which `git clone`s the repo (with
  git-lfs) and serves content over HTTP. This is the user's second pattern, and
  the LFS question becomes a deploy concern, not a pip concern.
  - **Operator caveat**: the git-lfs binary must be installed *before* the
    clone, or the working tree holds pointer stubs instead of real content
    (`git lfs install` once, then `git clone` / `git lfs pull`). The content is
    public, so no auth/token is involved. That is a one-line setup note, not a
    code path to build.

#### (B) Runtime fetch helper - NOT needed

A runtime fetch helper (a Python function pulling LFS content into `cache_fol`
on first use) was considered and **dropped**. Reasoning:

- Under (A) the only party that needs content on disk is the **operator running
  the service**. They get it by cloning with git-lfs installed, so the content
  materialises at clone time via standard tooling - there is nothing left for a
  helper to do.
- `lang-tutor` consumes content over HTTP and **never stores it locally**, so
  there is no consumer-side `cache_fol` to populate.
- A helper would only re-implement `git lfs pull`, and only for the narrow case
  of "want the content locally but won't install the git-lfs binary." Since the
  content is public and git-lfs is the standard path, this is maintenance
  burden for an edge case.

Recommendation: **library for code + service API (A) for content.** No fetch
helper.

- **Repo scaffolding**: new `lang-tutor` repo from `python-project-template`,
  reusing the same Params/Config/Singleton patterns; migrate
  `exercises/`, `progress/`, `webapp/`, `llm/tutor.py`, and the tutor service.
   ANS: yes

### Suggested next steps

Decided: `lang-tools` is a **library dependency for code only**; content is
delivered via the **service API (A)** over HTTP. No runtime fetch helper.
Webapp + tutor live in `lang-tutor`. Scaffold `lang-tutor` from
`python-project-template`.

1. Freeze the `lang-tools` public API (`Word`, sentence/conversation content
   models, the read/query functions, LLM chains) that `lang-tutor` will import.
2. Define the LFS content layout (words file(s) + sentences/conversations
   file(s), per-language) that the service reads from the cloned working tree.
3. Add the `lang-tools` read API (filtered word/sentence lookups over HTTP).
   Keep content out of the wheel; document the git-lfs setup step for operators.
4. Scaffold `lang-tutor` and move `exercises/` + `progress/` first (no LLM
   dependency), validating the cross-repo import works.
5. Move the webapp + `llm/tutor.py` + tutor service last, once the data
   dependency is stable.

### Migration order

Incremental, **lang-tools first, but extract before building the HTTP
endpoints** - not "endpoints first" and not "both at once". There are two
lang-tools surfaces: the **library surface** (importable models + query helpers
+ LLM chains, needed by both the split and the API) and the **HTTP read API**
(only the deployed runtime needs it, and it is the riskiest part). Stabilise the
cheap Python interface before introducing a network boundary.

- **Why not endpoints-first**: front-loads the hardest part (HTTP contract,
  serialization, deploy) against a content API whose shape is still moving;
  likely redone after the split clarifies what tutor needs.
- **Why not both-at-once**: introduces the repo boundary *and* the network
  boundary together, so a break could be either - two hard changes, one
  debugging surface.

Macro phases (one plan file each):

1. [`01_lib_freeze.md`](01_lib_freeze.md) - freeze the lang-tools library API
   and the LFS content layout in place (still one repo).
2. [`02_tutor_extract.md`](02_tutor_extract.md) - scaffold `lang-tutor`, migrate
   exercises + progress + webapp + tutor chain, coupled to lang-tools as a
   **library** (in-process content reads, no HTTP yet).
3. [`03_http_service.md`](03_http_service.md) - add the lang-tools HTTP read API
   and switch lang-tutor to consume content over HTTP.
