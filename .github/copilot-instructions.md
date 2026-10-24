# lang-tools - Copilot Instructions

## Project overview

`lang-tools` is the **content + data** half of a language-learning ecosystem (Portuguese-focused,
multi-language by design). It produces, models and serves vocabulary content, and holds no
per-learner state. Python 3.14, managed with **uv**. Package `lang_tools`.

- **Lexicon** - concept-centric model (`Lemma`, `Concept`, `Sense`, relation edges including
  look-alikes: false friends and cognates) for en, pt, es, fr, it; Parquet corpus behind
  `LexiconStore`; `LemmaCard` drill cards.
- **Build** - reproducible `build_initial` from Open Multilingual Wordnet (`wn`, CILI, `wordfreq`),
  re-applying the reviewed inputs under `data/curated/`.
- **LLM chains** - `llm-core` `StructuredLLMChain` wrappers for content and corpus maintenance, run
  over worklists by `llm.runner`.
- **Read API** - public FastAPI service (`lang_tools.webapp`) serving lemmas, concepts and cards.

## The lang-tutor boundary

The learner-facing app (exercises, progress, tutor chain, webapp) is the companion
[`lang-tutor`](https://github.com/Pitrified/lang-tutor) repo. It depends on `lang-tools` by git tag
and reads content over the read API, or in-process through the surface listed in
`docs/library/frozen_api.md`. Keep that surface stable; a change to it needs a new tag and a pin
bump in lang-tutor. `lang-tools` must never import `lang-tutor`.

## AI code development

At the end of the overall task assigned by the user, instead of ending the conversation, always use
the #askQuestions tool to ask the user if they want to add more details, features, or constraints
to the task.

## Running & tooling

Use the Makefile; it exists so commands are discoverable and consistent.

```bash
make help        # list every target
make sync        # uv sync --all-extras --all-groups
make hooks       # pre-commit install, once per clone
make check       # lint + typecheck + test
make docs        # mkdocs serve (make docs-build: strict, as CI)
make serve       # content read API on localhost:8010
```

**The pre-commit hooks run on every commit**, so write to pass them: ruff check and format,
pyright, stripped notebook outputs, no secrets, a single trailing newline. Never skip them with
`--no-verify`; fix the finding. `ruff` and `pyright` are pinned exactly and match the hook revs;
bump both together (`docs/guides/pre_commit.md`).

**Always run project code through `make`, or through `uv run --no-sync`.** A bare `uv run`
re-syncs the environment from `uv.lock` first, which silently reverts a local editable install
(`make dev-llm-core`, `make dev-fastapi-tools`). `make undev` is the deliberate way back. See
`docs/guides/makefile.md`.

Credentials live in `~/cred/lang-tools/.env` (template `nokeys.env`). Only `SAMPLE_API_KEY` is
required, with any value; `OPENAI_API_KEY` only to re-run an LLM job.

## Architecture

| Layer     | Path                                  | Role                                                              |
| --------- | ------------------------------------- | ----------------------------------------------------------------- |
| Lexicon   | `src/lang_tools/lexicon/`             | models, edges, `LexiconStore`, cards, quality gate, maintenance   |
| Ingestion | `src/lang_tools/lexicon/ingestion/`   | `build_initial`, sources, curated-input appliers, look-alike review |
| LLM       | `src/lang_tools/llm/`                 | chains and the checkpointed `runner`                              |
| Webapp    | `src/lang_tools/webapp/`              | `build_app()`, the read API routers                               |
| Language  | `src/lang_tools/language/`            | `Language` presets, normalisation, keyboard layouts               |
| Params    | `src/lang_tools/params/`, `config/`   | `get_lang_tools_params()`; env-aware params, pydantic config shapes |

The narrative for each layer is in `docs/library/`. Params follow the config / params split in
`docs/guides/params_config.md`.

## Data rules

- **Curated inputs, never hand edits.** Every LLM or agent job writes reviewed rows to a JSONL under
  `data/curated/`, and the build re-applies them, so a rebuild reproduces the corpus. Rebuild with
  `docs/guides/rebuild_corpus.md`.
- **`data/` is gitignored and stored through git LFS.** The seed (`bootstrap/`), the curated inputs
  and the review batches are committed with `git add -f`; the built corpus (`lexicon/`) stays local.
- **Latest row wins** for look-alikes: only the newest row per pair counts, and a later `unrelated`
  row retracts an edge. Reviews follow `.claude/skills/lookalike-review/` and the rulebook
  `docs/guides/lookalike_review.md`, whose hash is stored on every row: change it deliberately.
- **Paid LLM runs**: measure a small sample, report its cost, and get explicit approval before the
  full run (the notebooks gate this with `RUN_PAID`).

## Style rules

- Never use em dashes (`--`, `---`, or Unicode `—`). Use a hyphen `-` or rewrite the sentence.
- Use `loguru` (`from loguru import logger as lg`) for all logging.
- Raise descriptive named exceptions rather than bare `ValueError` / `RuntimeError`.
- Ruff runs with `select = ["ALL"]` and `target-version = "py314"`. Fix findings rather than adding
  `noqa`. Imports used only in annotations go under `if TYPE_CHECKING:`; the webapp is exempt
  because FastAPI reads route annotations at runtime, and a pydantic field type keeps its runtime
  import with `# noqa: TC00x` and the reason.

## Docstring style

**Google style** throughout, matching the rest of the fleet:

```python
def example(value: int) -> str:
    """One-line summary.

    Extended description as plain prose.

    Args:
        value: Description of the argument.

    Returns:
        Description of the return value.

    Raises:
        KeyError: If the key is missing.
    """
```

Never use NumPy / Sphinx RST underline headers (`Args\n----`). Section labels always take a
trailing colon. Module docstrings are narrative prose.

## Layout

- `tests/` mirrors `src/lang_tools/` and runs on the committed bootstrap seed, not the full corpus.
- `notebooks/` holds the thin drivers for the build and the maintenance jobs.
- `scratch_space/` holds the planning record and experiments: one numbered folder per initiative,
  `tracking.md` first (current: `scratch_space/09_concept_model/`).
- `docs/` is the MkDocs site: `guides/` for tooling and procedures, `library/` for narrative notes
  on the code, `reference/` generated from docstrings (never write files there). Keep it current
  at the end of every task, updating statements in place rather than appending history.
