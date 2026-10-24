# Pre commit

## Maintenance of the file

### Manually check the latest release versions

For

- pre-commit hooks versions
- yelp detect-secrets

1. open the repo link
2. go to releases
3. get the latest stable version

### Keep ruff and pyright in step with pyproject

`ruff` and `pyright` are pinned to an exact version in two places that must
agree: the `lint` group in `pyproject.toml` (`ruff==X`, `pyright[nodejs]==Y`,
used by `uv run`) and the `rev` in `.pre-commit-config.yaml` (used by the
hooks). If the two differ, the hook and `uv run ruff format` format the same
file differently and every commit picks up unrelated churn. Bump both together:

1. edit the exact pins in `pyproject.toml` and run `uv lock`
2. set the matching `rev` in `.pre-commit-config.yaml` (the revs carry a `v`
   prefix: `v0.15.17`, `v1.1.410`)
3. reformat the whole tree in its own commit, so the version bump and the
   formatting churn stay separate:

   ```bash
   make format
   uv run --no-sync pre-commit run --all-files
   ```

For `uv` itself and `nbstripout`, match the hook `rev` to the installed
version (`uv self update && uv --version`, `uv run --no-sync nbstripout --version`).
