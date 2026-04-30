# lang-tools - Copilot Instructions

## Project overview

`lang-tools` is a Python library that unifies the language-learning ecosystem (Portuguese-focused but multi-language by design). It centralises shared concerns previously scattered across `convo_craft`, `brazilian-bites`, `fala-comigo-ai-tutor`, `go-accenter`, and `worldly-words`:

- **Canonical language data models** - `Word`, `Language`, `UserWordProgress`, accent / normalization maps, exercise / progress schemas.
- **Exercise framework** - shared interfaces for sentence reconstruction, pair matching, conversational tutoring, diacritic typing, and Wordle-style guessing.
- **LLM service layer** - thin wrappers over `llm-core` `StructuredLLMChain` for translation, conversation generation, tutor correction, topic suggestion, and paragraph splitting.
- **Word ingestion** - pipelines for Wiktionary JSONL dumps, CSV imports, and LLM-generated content.
- **Unified FastAPI webapp** - single backend serving all exercise types with cross-app user progress (Google OAuth, session, CORS, rate limiting, Jinja2 + HTMX).

Python 3.13, managed with **uv**. Package name is `lang_tools`.

Long-form roadmap: `/home/pmn/ephem/linux-box-cloudflare/scratch_space/vibes/10-language-overview/`.

## Running & tooling

```bash
uv run pytest                        # run tests
uv run ruff check .                  # lint (ruff, ALL rules enabled)
uv run pyright                       # type-check (src/ and tests/ only)

uv run mkdocs serve                  # MkDocs local docs server

# webapp dev server
uvicorn lang_tools.webapp.app:app --reload
```

Credentials live at `~/cred/lang-tools/.env` (loaded by `load_env()` in `src/lang_tools/params/load_env.py`).

## Architecture layers

| Layer        | Path                                               | Role                                                                     |
| ------------ | -------------------------------------------------- | ------------------------------------------------------------------------ |
| Params       | `src/lang_tools/params/lang_tools_params.py`       | Singleton `LangToolsParams`; aggregates paths, sample, webapp params     |
| Paths        | `src/lang_tools/params/lang_tools_paths.py`        | `LangToolsPaths`; env-aware filesystem references                        |
| Config       | `src/lang_tools/config/`                           | Pydantic `BaseModelKwargs` models for typed settings (sample, webapp)    |
| Webapp       | `src/lang_tools/webapp/`                           | FastAPI app factory, routers, services, schemas, middleware              |
| Data models  | `src/lang_tools/data_models/basemodel_kwargs.py`   | `BaseModelKwargs` - Pydantic base with `to_kw()` kwargs flattening       |
| Metaclasses  | `src/lang_tools/metaclasses/singleton.py`          | `Singleton` metaclass                                                    |
| Env type     | `src/lang_tools/params/env_type.py`                | `EnvStageType` (dev/prod) and `EnvLocationType` (local/render) enums     |

Domain layers (planned, see roadmap):

| Layer        | Path                              | Role                                                                |
| ------------ | --------------------------------- | ------------------------------------------------------------------- |
| Language     | `src/lang_tools/language/`        | `Language` config, accent / normalization maps, keyboard layouts    |
| Words        | `src/lang_tools/words/`           | Canonical `Word` model and ingestion (Wiktionary, CSV, LLM)         |
| Progress     | `src/lang_tools/progress/`        | `UserWordProgress` and weighted selection algorithms                |
| Exercises    | `src/lang_tools/exercises/`       | Shared exercise interface and per-mechanic implementations          |
| LLM          | `src/lang_tools/llm/`             | `StructuredLLMChain` wrappers (translation, tutor, topics, etc.)    |

## Key patterns

**`LangToolsParams` singleton**  
Access project-wide config via `get_lang_tools_params()` from `src/lang_tools/params/lang_tools_params.py`. It aggregates `LangToolsPaths`, `SampleParams`, and `WebappParams`. Environment is controlled by `ENV_STAGE_TYPE` (`dev`/`prod`) and `ENV_LOCATION_TYPE` (`local`/`render`) env vars.

```python
from lang_tools.params.lang_tools_params import get_lang_tools_params

params = get_lang_tools_params()
paths = params.paths          # LangToolsPaths
webapp = params.webapp        # WebappParams
```

**`BaseModelKwargs`**  
Extend `BaseModelKwargs` (not plain `BaseModel`) for any config that needs to be forwarded as `**kwargs` to a third-party constructor. `to_kw(exclude_none=True)` flattens a nested `kwargs` dict at the top level.

```python
class SampleConfig(BaseModelKwargs):
    some_int: int
    nested_model: NestedModel
    kwargs: dict = Field(default_factory=dict)

cfg = SampleConfig(some_int=1, nested_model=NestedModel(some_str="hi"), kwargs={"extra": True})
cfg.to_kw(exclude_none=True)  # {"some_int": 1, "nested_model": ..., "extra": True}
```

**Config / Params separation**

- `src/lang_tools/config/` holds Pydantic `BaseModelKwargs` models that define the _shape_ of settings. Use `SecretStr` for every sensitive field. Never read env vars inside config models.
- `src/lang_tools/params/` holds plain classes that load _actual values_ and instantiate config models. Non-secret values are written as Python literals; env-switching is achieved via `match` on `env_type.stage` / `env_type.location`. Secrets are the only values loaded from `os.environ[VAR]` (raises `KeyError` naturally when missing).
- Every Params class accepts `env_type: EnvType | None = None` as its sole constructor argument. `__init__` only stores it and calls `_load_params()`. Loading is orchestrated via `_load_common_params()` then stage/location dispatch.
- Expose the assembled settings through `to_config()` returning the corresponding Pydantic model. Always mask secret fields in `__str__` using `[REDACTED]`.
- See `docs/guides/params_config.md` for the full reference with examples and common mistakes.

The canonical reference implementations are `src/lang_tools/config/sample_config.py` and `src/lang_tools/params/sample_params.py`.

**FastAPI webapp factory**  
`create_app(config?)` in `src/lang_tools/webapp/main.py` wires up middleware, routers, exception handlers, static files, and Jinja2 templates. Entry point for uvicorn: `lang_tools.webapp.app:app`.

Webapp config objects (`CORSConfig`, `SessionConfig`, `RateLimitConfig`, `GoogleOAuthConfig`) all extend `BaseModelKwargs` and live in `src/lang_tools/config/webapp/`.

**Env-aware paths**  
`LangToolsPaths.load_config()` dispatches on `EnvLocationType` (`LOCAL` / `RENDER`) to set environment-specific paths. Common paths (`root_fol`, `cache_fol`, `data_fol`, `static_fol`, `templates_fol`) are always set in `load_common_config_pre()`.

**`Singleton` metaclass**  
Use `metaclass=Singleton` for any class that must have exactly one instance per process (e.g., `LangToolsParams`). Reset in tests by clearing `Singleton._instances`.

## Style rules

- Never use em dashes (`--` or `---` or Unicode `—`). Use a hyphen `-` or rewrite the sentence.
- Use `loguru` (`from loguru import logger as lg`) for all logging.
- Raise descriptive custom exceptions (e.g., `UnknownEnvLocationError`) rather than bare `ValueError`/`RuntimeError`.

## Documentation

Always keep the `docs/` folder updated at the end of a task.

### Docs folder

- `docs/` holds MkDocs source. `mkdocs.yml` configures the site with the Material theme, mkdocstrings for API reference.
- `docs/guides/` holds narrative guides related to tooling, setup, and project conventions. These are not part of the API reference and should not be written in docstring style.
- `docs/library/` holds description of the core library code. This is not an API reference; write in narrative style with custom headings as needed. Can create subfolders for different domains.
- `docs/reference/` is a virtual folder generated by `mkdocstrings` from docstrings in the source code. Do not write any files here; write docstrings in the source code instead. To reference a file inside this section, link using this structure: [`<some class/function name>`](,,/../reference/lang_tools/config/sample_config/) which would link to `src/lang_tools/config/sample_config.py`'s API reference page.

### Docstring style

Use **Google style** throughout. mkdocstrings is configured with `docstring_style: "google"`.

Standard sections use a label followed by a colon, with content indented by 4 spaces:

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

    Example:
        Brief usage example::

            result = example(42)
    """
```

**Never use NumPy / Sphinx RST underline-style headers** (`Args\n----`, `Returns\n-------`, `Attributes\n----------`, etc.).

Rules:
- Section labels: `Args:`, `Returns:`, `Raises:`, `Attributes:`, `Note:`, `Warning:`, `See Also:`, `Example:`, `Examples:` - always with a trailing colon, never with an underline.
- `Attributes:` in class docstrings uses two levels of indentation: the attribute name at +4 spaces, its description at +8 spaces.
- Module docstrings are narrative prose. Custom topic headings (e.g., "Pattern rules") are written as plain labelled paragraphs (`Pattern rules:`) - no underline, no RST heading markup.
- `See Also:` lists items as bare lines indented under the section label, not as `*` bullets.

## Testing & scratch space

- Tests live in `tests/` mirroring `src/lang_tools/` structure.
- `scratch_space/` holds numbered exploratory notebooks and scripts. Not part of the package; ruff ignores `ERA001`/`F401`/`T20` there.

## Linting notes

- `ruff.toml` targets Python 3.13 with `select = ["ALL"]`. Key ignores: `COM812`, `D104`, `D203`, `D213`, `D413`, `FIX002`, `RET504`, `TD002`, `TD003`.
- Tests additionally allow `ARG001`, `INP001`, `PLR2004`, `S101`.
- Notebooks (`*.ipynb`) additionally allow `ERA001`, `F401`, `T20`.
- `meta/*` additionally allows `INP001`, `T20`.
- `max-args = 10` (pylint).

## End-of-task verification

After every code change, run the full verification suite before considering the task done:

```bash
uv run pytest && uv run ruff check . && uv run pyright
```

Then update the docs.
