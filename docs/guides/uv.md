# UV package manager

## Dependencies group

To add a package to a specific group, use the `--group` option:

```bash
uv add --group test pytest-cov
```

## Sync

Always sync everything with `make sync` (`uv sync --all-extras --all-groups`); a narrower sync
removes what it was not asked for. Run project code through `make` or `uv run --no-sync`: a bare
`uv run` syncs first and reverts a local editable install, see [Makefile](./makefile.md).

## Upgrade packages

`ruff` and `pyright` are pinned exactly and move together with the pre-commit
revs; see [Pre commit](./pre_commit.md). The commands below are for the other,
range-pinned packages.

Upgrades the lock, but not the dependencies in `pyproject.toml`.

```bash
uv lock --upgrade-package pydantic
```

If you want to upgrade the dependencies in `pyproject.toml`, use:

```bash
uv add "pydantic>=2.12"
```

If you want to upgrade the lock for all packages, use:

```bash
uv lock --upgrade
uv sync --all-extras --all-groups
```
