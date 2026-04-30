# Lang tools

`lang-tools` is a Python library that unifies the language-learning ecosystem
(Portuguese-focused, multi-language by design). It centralises shared concerns
previously scattered across `convo_craft`, `brazilian-bites`,
`fala-comigo-ai-tutor`, `go-accenter`, and `worldly-words`:

- Canonical language data models (`Word`, `Language`, `UserWordProgress`,
  accent / normalization maps).
- Shared exercise framework: sentence reconstruction, pair matching,
  conversational tutoring, diacritic typing, Wordle-style guessing.
- LLM service layer over `llm-core` for translation, conversation generation,
  tutor correction, topic suggestion.
- Word ingestion pipelines (Wiktionary JSONL, CSV, LLM-generated).
- Unified FastAPI webapp serving all exercise types with cross-app user
  progress (Google OAuth, Jinja2 + HTMX).

The full roadmap lives at
`linux-box-cloudflare/scratch_space/vibes/10-language-overview/`.

## Installation

### Setup `uv`

To install the package:

Setup [`uv`](https://docs.astral.sh/uv/getting-started/installation/).

### Install the package

Run the following command:

```bash
uv sync --all-extras --all-groups
```

## Docs

Docs are available at [https://pitrified.github.io/lang-tools/](https://pitrified.github.io/lang-tools/).

## Setup

### Environment Variables

To setup the package, create a `.env` file in `~/cred/lang_tools/.env` with the following content:

```bash
LANG_TOOLS_SAMPLE_ENV_VAR=sample
```

And for VSCode to recognize the environment file, add the following line to the
workspace [settings file](.vscode/settings.json):

```json
"python.envFile": "/home/pmn/cred/lang_tools/.env"
```

Note that the path to the `.env` file should be absolute.

### Pre-commit

To install the pre-commit hooks, run the following command:

```bash
pre-commit install
```

Run against all the files:

```bash
pre-commit run --all-files
```

### Linting

Use pyright for type checking:

```bash
uv run pyright
```

Use ruff for linting:

```bash
uv run ruff check --fix
uv run ruff format
```

### Testing

To run the tests, use the following command:

```bash
uv run pytest
```

or use the VSCode interface.

## IDEAs

- [ ] Phase 1: shared data layer (`Word`, `Language`, `UserWordProgress`)
- [ ] Phase 2: shared exercise framework (5 mechanics)
- [ ] Phase 3: shared LLM service via `llm-core`
- [ ] Phase 4: unified FastAPI webapp
