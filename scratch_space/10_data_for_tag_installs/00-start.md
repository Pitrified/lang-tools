# Data for tag installs - start

Status: open, not scheduled. Spun off while switching `lang-tutor` from a `[tool.uv.sources]`
path override to the `lang-tools @ v0.2.0` git-tag pin.

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

## Current answer

`in_process` runs against a local checkout installed with `make dev-lang-tools` (lang-tutor's
Makefile), which reads that checkout's `data/`. The override lives only in `.venv`: `make`
targets keep it (`uv run --no-sync`), a bare `uv run` or any `uv sync` reverts it, and
`make undev` reverts it on purpose. See lang-tutor's `docs/guides/makefile.md`.

No data-path setting or other workaround for now.

## To assess (not now)

- **Does a tag install need any data at all?** List what a consumer would read from disk, as
  opposed to over the read API. If the answer is "nothing", `make dev-lang-tools` stays the
  answer and this folder closes.
- **If some data is needed, it has to be shipped.** Decide what (the bootstrap seed, a slice, the
  full corpus), in what form, and how it is versioned against the code tag. Measure sizes first:
  `docs/guides/rebuild_corpus.md` measures the five-language `data/lexicon/` at about 35 MB,
  while `frozen_api.md` (LFS quotas) quotes about 135 MB for the en/pt Parquet; reconcile the two.
- **How it is shipped.** Candidates to weigh, none chosen: inside the wheel, as package data;
  a release asset per tag; a data repo or LFS checkout the consumer points at. Each changes the
  licensing picture (phase 10) and the LFS bandwidth picture.
- **How a consumer finds it.** Only once the above is settled, since the answer may make the
  path question disappear.
