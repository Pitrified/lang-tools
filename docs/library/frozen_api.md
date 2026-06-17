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
- `LexiconStore`, `get_store` - the read/query store over the whole graph.
- `get_all_lemmas`, `get_lemma_by_id`, `get_lemmas_by_language`,
  `get_lemmas_by_topic`, `get_lemmas_filtered` - lemma read/query helpers.
- `get_all_concepts`, `get_concept_by_id`, `concepts_for_lemma`,
  `lemmas_for_concept`, `senses_for_lemma`, `senses_for_concept`,
  `get_false_friends_for_lemma`, `concept_relations_for` - concept/sense/edge
  read helpers.
- `NotHydratedError`, `SenseNotHydratedError` - raised by the `resolve_*`
  back-reference accessors before the store hydrates an object.

The default store loads the Parquet corpus from disk lazily on first use (see the
content layout below); importing `lang_tools.lexicon` never touches disk.

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
  bootstrap/                          # committed JSONL sample seed (text, diffable)
    lemmas.jsonl  concepts.jsonl  senses.jsonl
    false_friends.jsonl  concept_relations.jsonl
    lexicon/                          # seed Parquet built from the JSONL (gitignored)
  lexicon/                            # real source-of-truth Parquet (gitignored, built)
    _store.sqlite                     # derived runtime cache (gitignored, never shipped)
```

- **Sample seed**: the committed `data/bootstrap/*.jsonl` files (the lean codec
  row shape) are a dev **input**, not a runtime source. The store reads Parquet
  only: `parquetize_seed.ipynb` turns the seed into its **own** Parquet corpus
  under `data/bootstrap/lexicon/` (gitignored) so a seed build never pollutes the
  real corpus. The ingestion phase produces the full corpus under `data/lexicon/`.
  `lang_tools.lexicon.lemma_store` builds the SQLite runtime engine from whichever
  Parquet corpus it is pointed at (via `LangToolsPaths.data_fol`), raising
  `CorpusNotFoundError` when none is present. The engine persists a
  `_store.sqlite` cache next to the Parquet; it is **derived** (rebuilds itself
  when the Parquet changes) and is never committed or shipped.
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

### When (and how) the Parquet reaches GitHub

> Beginner note. Short version: **the Parquet is not on GitHub yet.** It is a
> local build artifact. Today only the JSONL seed under `data/bootstrap/` is
> committed; everything you build under `data/lexicon/` (and
> `data/bootstrap/lexicon/`) stays on your machine.

This is intentional, not a bug. Two rules are in play and they look like they
disagree:

- `.gitignore` has `data/`, so `git add data/lexicon/...` is **silently ignored**
  - nothing under `data/` is staged unless you force it.
- `.gitattributes` has `data/** filter=lfs`, so anything that *does* get staged
  under `data/` is stored through git LFS rather than inline.

So the seed JSONL is committed because it was force-added past the ignore (`git
add -f`); it then rode the LFS filter. The built Parquet has simply never been
force-added, so it has never been uploaded. `run_service.md` describes this
interim state ("LFS-tracked; gitignored until the ingestion phase ships it").

**To see what *is* on GitHub:** open `data/bootstrap/lemmas.jsonl` in the GitHub
web UI. Because it is an LFS object you will see a "Stored with Git LFS" banner
with the file size and a download button, not the JSON inline. The Parquet files
do not appear at all yet.

**To publish a built corpus (producer side), when you decide to ship it:**

```bash
git lfs install                       # once per machine
git add -f data/lexicon              # force past the data/ ignore; LFS filter applies
git commit -m "ship full lexicon corpus"
git push                              # uploads the LFS blobs to GitHub
```

Do **not** add `data/lexicon/_store.sqlite` (or the `*.sig` file) - it is the
derived runtime cache and rebuilds locally on first load.

#### LFS storage and bandwidth quotas

Mind GitHub's LFS quotas before pushing a multi-language corpus (the en/pt
Parquet alone is ~135 MB). The current allowances, per
[GitHub's docs](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-storage-and-bandwidth-usage):

- **Per account, not per repository.** Quota belongs to the account that owns the
  repo (here, the `Pitrified` user), pooled across all that account's repos - not
  to each repo and not to each collaborator.
- **Free / Pro:** 10 GiB storage **and** 10 GiB bandwidth. **Team / Enterprise
  Cloud:** 250 GiB each.
- **Cadence is monthly (per billing cycle).** Both the accrued storage total and
  the bandwidth allowance reset to zero at the start of each billing cycle.
- **Bandwidth = downloads only.** Every clone or `git lfs pull` of an LFS blob
  counts against the *repo owner's* bandwidth; uploads (your `git push`) do not.
  A public corpus that many people pull can burn bandwidth fast.
- **Over quota:** with a `$0` spending limit, LFS is *blocked* for the rest of the
  month once you exceed it (pushes and pulls fail); with no limit set you are
  billed for the overage. Pre-paid data packs are gone, replaced by metered
  billing at roughly **$0.07 / GiB-month storage** and **$0.0875 / GiB
  bandwidth** (see
  [Git LFS billing](https://docs.github.com/en/billing/managing-billing-for-git-large-file-storage/about-billing-for-git-large-file-storage)).

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
