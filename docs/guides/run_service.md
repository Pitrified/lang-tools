# Running the content read service

`lang-tools` serves vocabulary content over HTTP so a consumer like `lang-tutor`
can consume it without an in-process dependency on the content store.
This is the operator guide: clone the repo with the content materialised, then
run the service.

The content is **public** - the read API requires no authentication or token.

## 1. Install git-lfs *before* cloning

The content under `data/` is tracked with [git LFS](https://git-lfs.com/). The
LFS binary must be installed and registered **before** you clone, or the working
tree holds pointer stubs (a few lines of text) instead of the real content.

```bash
# Install the binary (Debian/Ubuntu shown; use your package manager)
sudo apt-get install git-lfs

# Register the global smudge/clean filters (once per machine)
git lfs install
```

## 2. Clone and materialise the content

```bash
git clone https://github.com/Pitrified/lang-tools.git
cd lang-tools

# If you cloned before installing git-lfs, pull the real blobs now:
git lfs pull
```

Verify the content is real and not a pointer stub:

```bash
head -1 data/bootstrap/pt.csv   # should be the CSV header, not "version https://git-lfs..."
```

## 3. Install dependencies (including the webapp extra)

The service depends on `fastapi-tools`, declared as the `webapp` optional
dependency:

```bash
uv sync --all-extras --group dev
```

## 4. Run the service

Run on port `8010` to avoid colliding with a `lang-tutor` webapp on `8000`:

```bash
# Module entry point (reads host/port from WebappParams)
WEBAPP_PORT=8010 uv run python -m lang_tools.webapp.app

# Or drive uvicorn directly
uv run uvicorn lang_tools.webapp.app:app --host 127.0.0.1 --port 8010
```

Check it is up:

```bash
curl -s http://127.0.0.1:8010/health
curl -s "http://127.0.0.1:8010/api/v1/lemmas?language=pt"
```

!!! note "Trusted hosts"
    The fastapi-tools middleware rejects requests whose `Host` header is not in
    the configured trusted hosts unless debug mode is on. For local development
    set `WEBAPP_DEBUG=true`; for a deployment configure the trusted hosts and a
    `SESSION_SECRET_KEY` as you would for any fastapi-tools app.

## Read API

All endpoints are public and return JSON `Lemma` objects (the same model
`lang-tutor` imports), including the computed fields `id`, `has_accent`,
`accented_chars`, and `length`.

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/lemmas` | List lemmas. Optional query params `language` (ISO 639-1) and `topic`. |
| `GET` | `/api/v1/lemmas/{lemma_id}` | Fetch one lemma by its deterministic id. `404` when absent. |
| `GET` | `/health` | Liveness/health probe (from fastapi-tools). |

Example:

```bash
curl -s "http://127.0.0.1:8010/api/v1/lemmas?language=pt&topic=basics"
curl -s "http://127.0.0.1:8010/api/v1/lemmas/bf1c1f94e4bca388"
```

`lang-tutor` points at this service with `LANG_TOOLS_BASE_URL`; see its
content-source guide for the consumer side.
