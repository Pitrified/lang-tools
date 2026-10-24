# Getting Started

This guide will help you set up your development environment and get started with the project.

## Prerequisites

- Python 3.14
- [uv](https://docs.astral.sh/uv/) package manager

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Pitrified/lang-tools.git
cd lang-tools
```

### 2. Install Dependencies

```bash
# Install everything: all extras and all dependency groups
uv sync --all-extras --all-groups
```

Use this full form. A narrower `uv sync` removes what it was not asked for, so
syncing a single group later drops the extras (`store`, `ingest`) and the
tests that need `duckdb`, `wn` and `wordfreq` fail to collect.

### 3. Verify Installation

```bash
# Run tests
uv run pytest

# Check code style
uv run ruff check .

# Type checking
uv run pyright
```

## Development Workflow

### Running Tests

```bash
uv run pytest
uv run pytest -v              # Verbose output
uv run pytest tests/config/   # Run specific test directory
```

### Code Quality

```bash
# Lint and format
uv run ruff check .
uv run ruff format .

# Type checking
uv run pyright
```

### Pre-commit Hooks

Pre-commit hooks are configured to run automatically on each commit:

```bash
# Install hooks (first time only)
uv run pre-commit install

# Run manually on all files
uv run pre-commit run --all-files
```

## Environment Configuration

The project expects environment variables to be stored in `~/cred/lang-tools/.env`.

!!! warning "Security"
    Never commit `.env` files or secrets to the repository.

## Building Documentation

```bash
# Start local server with hot reload
uv run mkdocs serve

# Build static site
uv run mkdocs build
```
