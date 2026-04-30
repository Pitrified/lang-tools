# Lang Tools

Welcome to the **Lang Tools** documentation.

`lang-tools` is a Python library that unifies the language-learning ecosystem
(Portuguese-focused, multi-language by design). It centralises shared concerns
previously scattered across `convo_craft`, `brazilian-bites`,
`fala-comigo-ai-tutor`, `go-accenter`, and `worldly-words` into a single
package: canonical data models, an exercise framework, an LLM service layer,
word ingestion pipelines, and a unified FastAPI webapp.

The full design roadmap lives at
`linux-box-cloudflare/scratch_space/vibes/10-language-overview/`.

## Features

- **Canonical data models** for words, languages, accent maps, and user progress.
- **Shared exercise framework** covering sentence reconstruction, pair matching,
  conversational tutoring, diacritic typing, and Wordle-style guessing.
- **LLM services** layered on `llm-core` for translation, conversation
  generation, tutor correction, and topic suggestion.
- **Word ingestion** from Wiktionary JSONL dumps, CSV files, and LLM output.
- **Unified FastAPI webapp** with Google OAuth, sessions, CORS, rate limiting,
  Jinja2 + HTMX.
- Modern Python 3.13+, managed with [uv](https://docs.astral.sh/uv/).
- Pre-configured Ruff, Pyright, pytest, pre-commit, and MkDocs.

## Quick Start

```bash
git clone https://github.com/Pitrified/lang-tools.git
cd lang-tools

uv sync --all-extras --all-groups

uv run pytest
uv run mkdocs serve
uvicorn lang_tools.webapp.app:app --reload
```

## Project Structure

```
lang-tools/
├── src/lang_tools/       # Main package
│   ├── config/             # Pydantic config models
│   ├── data_models/        # BaseModelKwargs and shared models
│   ├── metaclasses/        # Singleton metaclass
│   ├── params/             # Env-aware params and paths
│   └── webapp/             # FastAPI app, routers, middleware
├── tests/                  # Test suite mirroring src/
├── docs/                   # MkDocs source (you are here)
└── scratch_space/          # Experimental notebooks and vibes
```

## Next Steps

- [Getting Started](getting-started.md) - Set up your development environment.
- [Guides](guides/uv.md) - Tooling and project conventions.
- [API Reference](reference/) - Auto-generated from docstrings.
- [Contributing](contributing.md) - How to contribute.
