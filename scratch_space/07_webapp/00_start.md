# Webapp

## Overview

A single FastAPI application serving all language-learning exercise types,
following kit-hub / fastapi-tools patterns (HTMX + Jinja2 frontend).

Context docs:

- `linux-box-cloudflare/scratch_space/vibes/10-language-overview/05-unified-webapp.md`
- `linux-box-cloudflare/scratch_space/vibes/10-language-overview/00-language-overview.md`
- `lang-tools/README.md`

## Plan

### Frontend: HTMX + Jinja2

Server-rendered templates with HTMX for interactivity.
For exercises needing rich client-side interactions (wordle tile animations,
diacritic keyboard, drag-and-drop reconstruction), use vanilla JS or Alpine.js
within the Jinja2 templates. No separate SPA build step.

### Routing structure

| Group | Endpoints | Purpose |
|-------|-----------|---------|
| Exercises | `POST /exercises/{type}/start`, `submit`, `finish` | Start a round, submit an answer, end session |
| Exercises | `GET /exercises/{type}/config` | Exercise-specific settings |
| Words | `GET /words`, `GET /words/{id}`, `POST /words/{id}/useless` | Browse, detail, mark useless |
| Progress | `GET /progress`, `GET /progress/{language}`, `GET /progress/words` | Dashboard, per-language, per-word stats |
| Languages | `GET /languages`, `GET /languages/{code}` | Available languages and config |

Exercise types: `sentence-reconstruction`, `pair-matching`, `conversational-tutor`, `diacritic-typing`, `wordle`.

### App structure

```
src/lang_tools/webapp/
  main.py                  # create_app() factory (fastapi-tools pattern)
  app.py                   # uvicorn entrypoint
  routers/
    exercises.py           # /exercises/* endpoints
    words.py               # /words/* endpoints
    progress.py            # /progress/* endpoints
    languages.py           # /languages/* endpoints
  services/                # Business logic layer
  schemas/                 # Pydantic request/response models
  templates/               # Jinja2 templates (base layout + per-exercise)
  static/                  # CSS, JS (Alpine.js, HTMX), images
```

### Authentication

Two modes controlled by `ENV_STAGE_TYPE`:

**Dev mode (`ENV_STAGE_TYPE=dev`)**

- Google OAuth is disabled entirely. No login flow, no session secret needed.
- A hardcoded dev user is injected automatically (e.g., `user_id="dev-user"`).
- The app starts with zero config beyond `ENV_STAGE_TYPE=dev`.
- Progress and preferences are still persisted to the DB under the dev user.

**Prod mode (`ENV_STAGE_TYPE=prod`)**

- Google OAuth + session cookies (from fastapi-tools).
- Requires `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SESSION_SECRET_KEY` in env.
- Anonymous mode: UUID in cookie, progress persisted server-side.

### Setup guide (part of implementation)

Write a `docs/guides/webapp_setup.md` covering:

1. Install deps (`uv sync --all-extras --all-groups`).
2. Dev mode quickstart: set `ENV_STAGE_TYPE=dev`, run `uvicorn lang_tools.webapp.app:app --reload`. No `.env` file needed.
3. Prod mode: create `~/cred/lang-tools/.env` with OAuth + session secrets, set `ENV_STAGE_TYPE=prod` and `ENV_LOCATION_TYPE=local` or `render`.
4. Database setup: run Alembic migrations.
5. Seeding words: how to run the ingestion pipeline.

### Database

SQLAlchemy ORM + Alembic migrations (same pattern as kit-hub).

Tables: `words`, `languages`, `user_word_progress`, `user_preferences`, `exercise_sessions`.

### Exercise state

Client-side. Each exercise page holds its round state in JS and sends it
with each request. Simpler than server-side session/Redis; cheating is
acceptable for a personal learning tool.

### Deployment

Render (single web service + managed Postgres), same as kit-hub/media-downloader.
`render.yaml` for infra-as-code.

### Implementation phases

1. **Scaffold** - `create_app()` factory, health router, static/templates wiring, base layout template.
2. **Words + Languages** - word browsing pages, language selector, data seeding (Wiktionary JSONL + CSV import).
3. **Progress** - `UserWordProgress` model, weighted selection algorithm, dashboard page.
4. **Exercise: pair-matching** - simplest exercise, good first integration test of the full loop.
5. **Exercise: wordle** - needs client-side JS for tile animation + virtual keyboard.
6. **Exercise: diacritic-typing** - on-screen accented keyboard, hint system.
7. **Exercise: sentence-reconstruction** - drag-and-drop or tap-to-order shuffled portions.
8. **Exercise: conversational-tutor** - LLM-powered chat (via `llm-core` `StructuredLLMChain`), topic generation.
9. **Auth + deploy** - Google OAuth, Render deployment, env-aware config.

### Key dependencies

- `fastapi-tools` - Google OAuth, session, CORS, rate limiting, Jinja2 templates, HTMX helpers
- `llm-core` - `StructuredLLMChain` for translation, conversation generation, tutor correction, topic suggestion
- `python-tools` - `BaseModelKwargs`, `Singleton`, `EnvType`

### Open decisions

- Word list source for wordle validation: load ~12k words into an in-memory set at startup for O(1) lookup.
- Template structure: one base layout with exercise-specific blocks vs separate full templates per exercise.
- Alpine.js vs vanilla JS for interactive exercise components.
