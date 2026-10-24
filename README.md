# Lang tools

`lang-tools` is the content + data half of a language-learning ecosystem
(Portuguese-focused, multi-language by design). The learner-facing app
(exercises, progress, tutor, webapp) is the companion `lang-tutor` repo, which
reads content from here.

- A concept-centric lexicon (`Lemma`, `Concept`, `Sense`, relation edges
  including false friends and cognates) for en, pt, es, fr and it, built
  reproducibly from Open Multilingual Wordnet plus reviewed curated inputs.
- `LemmaCard` drill cards and a public FastAPI read API serving them.
- Content-producing LLM chains over `llm-core`.

The full roadmap lives at
`linux-box-cloudflare/scratch_space/vibes/10-language-overview/`.

## Installation

### Setup `uv`

To install the package:

Setup [`uv`](https://docs.astral.sh/uv/getting-started/installation/).

### Install the package

Run the following command:

```bash
make sync        # uv sync --all-extras --all-groups
```

## Docs

Docs are available at [https://pitrified.github.io/lang-tools/](https://pitrified.github.io/lang-tools/).

## Setup

### Environment Variables

To setup the package, create a `.env` file in `~/cred/lang-tools/.env` with the following content:

```bash
LANG_TOOLS_SAMPLE_ENV_VAR=sample
```

And for VSCode to recognize the environment file, add the following line to the
workspace [settings file](.vscode/settings.json):

```json
"python.envFile": "/home/pmn/cred/lang-tools/.env"
```

Note that the path to the `.env` file should be absolute.

### Development

Every command is a `make` target; `make help` lists them.

```bash
make hooks       # install the pre-commit hooks, once per clone
make check       # lint, typecheck and test
make format      # ruff format
make docs        # serve the docs
```

Run project code through `make` or `uv run --no-sync`, never a bare `uv run`: see
`docs/guides/makefile.md`. `ruff` and `pyright` are pinned exactly and match the hook revs; bump
both together (see `docs/guides/pre_commit.md`).
