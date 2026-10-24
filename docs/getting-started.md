# Getting Started

This guide will help you set up your development environment and get started with the project.

## Prerequisites

- Python 3.14
- [uv](https://docs.astral.sh/uv/) package manager
- [git LFS](https://git-lfs.com/)

## Installation

### 1. Clone the Repository

Register git LFS **before** cloning, so the committed seed (`data/bootstrap/`) and the curated
inputs (`data/curated/`) arrive as real content rather than pointer stubs:

```bash
git lfs install
git clone https://github.com/Pitrified/lang-tools.git
cd lang-tools
git lfs pull   # only needed if you cloned before installing git LFS
```

An older clone, from before `data/` moved to LFS, may refuse to pull or ask for a password on
the public repo; [Rebuild the corpus](guides/rebuild_corpus.md#troubleshooting) has both fixes.

The tests run on the seed, and the corpus build re-applies the curated inputs. The built corpus
itself is not committed; [Rebuild the corpus](guides/rebuild_corpus.md) builds it.

### 2. Install Dependencies

```bash
make sync        # uv sync --all-extras --all-groups
make hooks       # install the pre-commit hooks, once per clone
```

`make sync` is the full form on purpose. A narrower `uv sync` removes what it was not asked for, so
syncing a single group later drops the extras and the tests that need them fail to collect.

### 3. Verify Installation

```bash
make check       # lint, typecheck and test
```

## Development Workflow

`make help` lists every target. Run project code through `make` or `uv run --no-sync`, never a
bare `uv run`; [Makefile](guides/makefile.md) explains why.

```bash
make check                            # before every commit
make format                           # ruff format
uv run --no-sync pytest tests/lexicon/   # one test directory
```

The pre-commit hooks run on each commit; run them all by hand with
`uv run --no-sync pre-commit run --all-files`.

## Environment Configuration

The project expects environment variables to be stored in `~/cred/lang-tools/.env`.

!!! warning "Security"
    Never commit `.env` files or secrets to the repository.

## Building Documentation

```bash
make docs        # local server with hot reload
make docs-build  # strict build, as CI
```
