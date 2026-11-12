---
status: draft
priority: 1
description: |
  How the corpus reaches anyone who is not running the build: what is shipped (the seed, a
  slice, the full corpus), in what form, how it is versioned against the code tag, and how a
  consumer finds it. A git-tag install carries the code and no data today.
---

# Distribution - start

## Original note

From the licensing plan, phase 10 of `09_concept_model`:

> **Distribution shape** - how the dataset is published/versioned (git-LFS layout from phase 3,
> release tagging), if publishing externally.

It moved out of licensing into its own folder, since it is the next thing to work on and would
turn licensing into a much larger feature.
The licensing plan stays [`../09_concept_model/10_licensing_docs.md`](../09_concept_model/10_licensing_docs.md),
and the two meet at one point: what is shipped, and how, decides which licenses and attributions
travel with it.

It also takes in [`10_data_for_tag_installs`](../10_data_for_tag_installs/00_start.md),
now superseded, whose questions were the same ones seen from lang-tutor's side.
Its analysis is carried below.

## The problem

A git-tag install of `lang-tools` carries the code and no data, so anything that reads the corpus
from disk finds nothing.

- `LangToolsPaths` resolves every folder from the installed package:
  `root_fol = Path(lang_tools.__file__).parent.parents[1]`, `data_fol = root_fol / "data"`.
  In a checkout that is the repo's `data/`. In a tag install the package sits in the consumer's
  `.venv`, and `data/` points at a folder that does not exist.
- Nothing overrides that path: `load_local_config` / `load_render_config` are empty, and
  `get_store()` builds the store from `get_lang_tools_params().paths.data_fol`.
- By design the corpus is not in the wheel (`docs/library/frozen_api.md`, "Content is not in the
  wheel"): `data/` is gitignored, stored through git LFS, and the built Parquet is local to
  whoever ran the build.

## Who it hits

`lang-tutor` reads content in one of two modes (`LANG_TOOLS_CONTENT_SOURCE`):

| Mode | Reads | With a tag install |
| --- | --- | --- |
| `http` (default) | the lang-tools read API | works: only the Python surface is needed |
| `in_process` | the lang-tools store, from disk | no corpus to open |

Its test suite reads no corpus, so it passes either way.
Anyone else who wants the dataset itself, without running the build, has no way to get it.

## Current answer

`in_process` runs against a local checkout installed with `make dev-lang-tools` (lang-tutor's
Makefile), which reads that checkout's `data/`. The override lives only in `.venv`: `make`
targets keep it (`uv run --no-sync`), a bare `uv run` or any `uv sync` reverts it, and
`make undev` reverts it on purpose. See lang-tutor's `docs/guides/makefile.md`.

No data-path setting or other workaround for now.

## To assess

- **Who consumes the data from disk?** lang-tutor's `in_process` mode, and an external user of
  the dataset if it is published. List what each would read, as opposed to over the read API.
- **What is shipped.** The bootstrap seed, a slice, or the full corpus; in what form; and how it
  is versioned against the code tag. Measure sizes first: `docs/guides/rebuild_corpus.md`
  measures the five-language `data/lexicon/` at about 35 MB, while `frozen_api.md` (LFS quotas)
  quotes about 135 MB for the en/pt Parquet; reconcile the two.
- **How it is shipped.** Candidates to weigh, none chosen: inside the wheel, as package data;
  a release asset per tag; a data repo or LFS checkout the consumer points at; a dataset host.
  Each changes the licensing picture and the LFS bandwidth picture.
- **How a consumer finds it.** Only once the above is settled, since the answer may make the
  path question disappear.
