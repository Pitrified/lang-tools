# Lang Tools

Welcome to the **Lang Tools** documentation.

`lang-tools` is the **content + data** service for the language-learning
ecosystem (Portuguese-focused, multi-language by design): canonical data
models, word ingestion pipelines, and the content-producing LLM chains. The
learner-facing concerns (exercises, per-user progress, the tutor chain, and the
webapp) live in the companion `lang-tutor` repo, which depends on `lang-tools`
for content.

The full design roadmap lives at
`linux-box-cloudflare/scratch_space/vibes/10-language-overview/`; the
`lang-tools` / `lang-tutor` split is tracked under
`scratch_space/08_lang_tutor/`.

## Features

- **Canonical data models** for words, languages, and accent maps.
- **LLM services** layered on `llm-core` for translation, conversation
  generation, topic suggestion, paragraph splitting, greetings, and word
  generation.
- **Word ingestion** from Wiktionary JSONL dumps, CSV files, and LLM output.
- Modern Python 3.13+, managed with [uv](https://docs.astral.sh/uv/).
- Pre-configured Ruff, Pyright, pytest, pre-commit, and MkDocs.

## Quick Start

```bash
git clone https://github.com/Pitrified/lang-tools.git
cd lang-tools

uv sync --all-extras --all-groups

uv run pytest
uv run mkdocs serve
```

## Project Structure

```
lang-tools/
├── src/lang_tools/       # Main package
│   ├── config/             # Pydantic config models
│   ├── data_models/        # BaseModelKwargs and shared models
│   ├── language/           # Language presets and normalisation
│   ├── llm/                # Content-producing StructuredLLMChain wrappers
│   ├── metaclasses/        # Singleton metaclass
│   ├── params/             # Env-aware params and paths
│   └── words/              # Word model, ids, ingestion, word store
├── tests/                  # Test suite mirroring src/
├── docs/                   # MkDocs source (you are here)
└── scratch_space/          # Experimental notebooks and vibes
```

## Next Steps

- [Getting Started](getting-started.md) - Set up your development environment.
- [Guides](guides/uv.md) - Tooling and project conventions.
- [API Reference](reference/) - Auto-generated from docstrings.
- [Contributing](contributing.md) - How to contribute.
