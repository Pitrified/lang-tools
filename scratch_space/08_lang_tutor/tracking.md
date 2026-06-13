# implementation tracking

Splitting `lang-tools` into `lang-tools` (content + data service) and
`lang-tutor` (tutoring + exercises). Analysis and decisions in
[`00-start.md`](00-start.md).

## Coupling decision

- `lang-tools` = library dependency for **code only** (data models, `Word`,
  query helpers, LLM chains).
- **Content** (words + sentences) delivered via the **HTTP read API (service)**;
  no runtime fetch helper. Operator clones with git-lfs installed.
- Webapp + tutor live in `lang-tutor`. New repo from `python-project-template`.

## Migration order

lang-tools first, **extract before building the HTTP endpoints** (not
endpoints-first, not both-at-once). See "Migration order" in
[`00-start.md`](00-start.md).

## Phases

| # | Phase | Plan | Status |
| - | ----- | ---- | ------ |
| 1 | Freeze lang-tools library API + LFS content layout (in place) | [`01_lib_freeze.md`](01_lib_freeze.md) | done |
| 2 | Scaffold lang-tutor, migrate tutor concerns (library-coupled) | [`02_tutor_extract.md`](02_tutor_extract.md) | not started |
| 3 | Add lang-tools HTTP read API, switch lang-tutor to HTTP | [`03_http_service.md`](03_http_service.md) | not started |

Status values: not started / in progress / done.
