---
status: done
---

# Phase 4 - store layer + indexes

## Overview

Grow `lemma_store` (renamed in phase 1) from a flat lemma registry into the
read/query layer for the whole lexical graph: lemmas, concepts, senses, and the
decoupled edge tables, with the look-aside indexes the app needs and the
representation-layer hydration that phase 2 deferred here. It implements the
storage format and access engine decided in phase 3 over the models from phase 2.
Context: [`00-concepts-brainstorm.md`](00-concepts-brainstorm.md), "Storage and
indexing"; [`02_core_models.md`](02_core_models.md), "Persistence vs
representation"; [`03_storage_indexing.md`](03_storage_indexing.md).

This phase is **plumbing, not payload**: it wires loaders, registries, indexes,
hydration, and query helpers, plus the HTTP read endpoints. It does **not**
produce the data (phase 5) or fill frequency/CEFR/relation values (phases 6-7);
it is exercised against a small fixture dataset.

Sequencing note (see "Sequencing with phase 3"): the **query surface defined
below is the design input phase 3 measures against**, so it is written first even
though the implementation waits on phase 3's format decision. Planning the two
phases together is deliberate - it sharpens phase 3's experiments and stops the
experiment code from being throwaway that this phase re-implements.

## Phase 3 inputs (decided, with numbers)

Phase 3 ran the experiments
([`03_storage_indexing/03.1_performance_tests.ipynb`](03_storage_indexing/03.1_performance_tests.ipynb))
and its decision now constrains this phase concretely:

- **Canonical format: Parquet (zstd), every table, partitioned per table and per
  language for the large ones (`senses`/`lemmas`), all under git-LFS** - one
  uniform distribution path, no normal-git JSONL artifact. The codec seam reads
  Parquet, not JSONL.
- **Two-tier runtime, gated by a measured memory cliff.** The full corpus as
  in-memory pydantic dicts is **~1.9 GB resident** (lemmas 745 MB @400k +
  concepts 77 MB + senses ~1,075 MB @1M), infeasible on a 512 MB dyno. The
  current all-resident dict store is therefore correct **only for the small
  bootstrap/sample data**; the full corpus must use **SQLite indexed point
  lookups** (~30 us, ~0 resident). This phase builds the store so the access
  engine is swappable behind the same query surface.
- **DuckDB is a build/QA tool, not the hot path** (point lookups ~16 ms, ~500x
  slower than a dict and ~550x an indexed SQLite read). It powers the `inspect`
  path over Parquet, never the per-request store.
- **Every filtered / adjacency read needs an explicit index.** A raw columnar /
  `LIKE` scan for the lang+topic filter was ~150 ms; the look-aside indexes below
  are not optional polish, they are the difference between ~0.1 us and ~150 ms.
- **`pyarrow` + `duckdb` graduate from phase-3 scratch installs into real
  `pyproject.toml` dependencies** when this phase lands (likely an extra, since
  only the store/inspect path needs them).
- **Inspect / edit workflow is part of this phase** (see Codec seam): nothing
  human-readable is committed, so reading and editing any table are explicit
  operations over the Parquet.

## Goals

1. Define the stable **read/query surface** for the whole graph (the contract
   `lang-tutor`, the webapp, and exercises consume) and the **access patterns**
   behind it - this doubles as phase 3's benchmark target.
2. Load and index every table (lemmas, concepts, senses, false-friend and
   concept-relation edges) behind a thin **codec seam** so the format chosen in
   phase 3 is swappable and the phase-3 experiment code promotes into the real
   loader instead of being rewritten.
3. Implement the **representation-layer hydration** phase 2 specified: populate
   the serialization-excluded back-references once at load time, with a single
   owner (the store) and a defined guard for unhydrated objects.
4. Extend the webapp with concept/relation read endpoints while keeping the lemma
   payload lean.
5. Keep `lang-tools` green over a fixture dataset with tests covering indexing,
   symmetry, hydration, and missing-id edge cases.

## Query surface & access patterns (the phase-3 benchmark target)

This is the contract and the exact set of reads phase 3 must measure. Each entry
notes the access pattern so the format/engine trade-off is grounded.

| Helper | Access pattern | Hot? |
| ------ | -------------- | ---- |
| `get_lemma_by_id(lemma_id)` | point lookup by primary key | **hot** |
| `get_lemmas_by_language(language)` | small filtered scan | warm |
| `get_lemmas_by_topic(topic)` / `get_lemmas_filtered(...)` | filtered scan | warm |
| `get_concept_by_id(concept_id)` | point lookup by primary key | **hot** |
| `concepts_for_lemma(lemma_id)` | adjacency over the sense table | **hot** |
| `lemmas_for_concept(concept_id, language=None)` | adjacency over the sense table, optionally bucketed by language | **hot** |
| `senses_for_lemma(lemma_id)` / `senses_for_concept(concept_id)` | adjacency over the sense table | warm |
| `get_false_friends_for_lemma(lemma_id)` | symmetric adjacency over the false-friend edges | warm |
| `concept_relations_for(concept_id, relation_type=None)` | typed/directional adjacency (phase 7 payload) | cold |

Characterisation for phase 3: the surface is **point lookups and bounded
adjacency joins**, not large aggregations. That favors in-memory dicts or SQLite
point lookups over a columnar analytical engine, and tells phase 3 exactly which
latencies to time (id lookups, sense-table adjacency, symmetric false-friend
fan-out) rather than guessing.

## Plan

All paths under `src/lang_tools/lexicon/` unless noted. The current
`lemma_store.py` already provides `_ALL_LEMMAS` / `_LEMMAS_BY_ID` and the lemma
getters; this phase generalises that pattern to every table.

### Codec seam (loader boundary)

- A thin `_load_table(name) -> list[<Model>]` / `_dump_table(name, rows)`
  boundary that hides the on-disk format behind a stable signature. Per phase 3
  the promoted codec is **Parquet (zstd)**; the phase-3 `write_parquet` /
  pyarrow-schema work is the seed for it (the JSONL/CSV/SQLite-sizing branches and
  the timing harness are discarded). The rest of the store imports only the seam,
  never pyarrow.
- **Nested columns** round-trip natively via the pyarrow schemas validated in
  phase 3: `topics`/`sources` as `list<string>`, `examples` as
  `list<struct<sentence,translation>>`, `definitions`/`explanation_notes` as
  `map<string,string>`. The lean persisted shape drops the cosmetic computed
  fields (`has_accent`/`accented_chars`/`length`); `id` is recomputed on load, so
  it need not be a stored column for the dict path but **is** kept as a column for
  the SQLite/Parquet index path.
- **Partitioning** is part of the seam: `_load_table("senses")` globs
  `data/lexicon/senses/*.parquet` (per-language files); `_load_table("senses",
  lang="en")` reads one. Writers emit per-language files for `senses`/`lemmas`,
  one file for the small tables.

### Inspect / edit tooling (phase 3 workflow, built here)

No CLI. The package exposes thin **functions** and a **notebook** drives them
interactively; all logic stays in the package so the same functions back tests
and any future tooling, and the notebook is only a caller.

- **Package functions (the real surface):**
  - `inspect_table(name, *, lang=None, where=None, limit=None)` - runs DuckDB SQL
    directly over the Parquet (no import step) and returns the rows (e.g.
    `list[dict]` / a pyarrow table) for read-only exploration and QA. DuckDB is
    confined to this one function.
  - `export_table(name, path, *, fmt="jsonl")` / `import_table(name, path)` for
    the edit round-trip: export -> hand/LLM-edit the transient JSONL ->
    `import_table`, which **validates every row through the pydantic model** (a
    renamed/missing column or bad value raises before anything is written) and
    rewrites the canonical Parquet. The JSONL is scratch, never committed;
    `export`/`import` reuse `_load_table` / `_dump_table` plus a JSONL
    (de)serializer.
- **Driver notebook:** a notebook under a **new general top-level `notebooks/`
  folder** (e.g. `notebooks/lexicon_corpus/explore.ipynb`), distinct from
  `scratch_space/` (which holds throwaway phase work) - this is the durable,
  package-level place to interact with the corpus. It imports the functions above
  and calls them to inspect / slice / edit any table; it introduces **no
  significant logic of its own**.
- **Schema changes are not edits:** adding/removing a column regenerates the
  table from the ingestion pipeline (phase 5), per the "no data migration"
  decision - never patched line-by-line.

### Registries

- Load each table at import (or lazily, per phase 3's memory finding):
  `_ALL_LEMMAS` / `_LEMMAS_BY_ID`, `_ALL_CONCEPTS` / `_CONCEPTS_BY_ID`,
  `_ALL_SENSES`, `_ALL_FALSE_FRIENDS`, `_ALL_CONCEPT_RELATIONS`.
- Primary-key dicts give the hot point lookups; the rest are derived indexes.

### Runtime modes (dict vs SQLite) - from phase 3's memory cliff

The store exposes **one query surface** over two interchangeable engines, chosen
by data size (the ~1.9 GB-resident finding):

- **Resident mode (default for the bootstrap/sample data):** load every table's
  Parquet into the dicts above and the look-aside indexes; serve lookups from
  memory. This is today's `lemma_store` generalised, and the mode where
  **eager full-graph hydration** (below) makes sense, since all objects are
  resident and can be wired to shared instances once at load.
- **SQLite mode (for the full corpus):** build a SQLite index *from* the Parquet
  at load (or ship a prebuilt one as a derived, non-canonical artifact) and serve
  the query surface via indexed `SELECT`s (~30 us point lookup, ~0 resident). The
  graph is **not** held resident, so it is not wired eagerly - but a fetched
  object **can still be hydrated on demand at fetch time** (bounded depth) by
  calling the same query methods, or callers can use the methods directly. See
  Hydration for the eager-vs-on-demand split. The look-aside indexes become
  SQLite secondary indexes / a normalised topic table (a raw `LIKE`/scan was
  ~150 ms - not acceptable).

For this phase the **resident mode is implemented and tested** against the
fixture; the SQLite-mode seam (engine selection + query-method parity) is
specified here and the indexed implementation can follow once real data exists
(phase 5), so the store is never wedged to the all-resident assumption.

### Look-aside indexes

- `_SENSES_BY_LEMMA_ID` and `_SENSES_BY_CONCEPT_ID` (the adjacency that powers
  `concepts_for_lemma` / `lemmas_for_concept` / `senses_for_*`).
- `_FALSE_FRIENDS_BY_LEMMA_ID`: built by inserting each edge under **both**
  endpoints, since the persisted edge is canonically ordered (`lemma_id_a <
  lemma_id_b`) and stored once (see phase 2).
- `_CONCEPT_RELATIONS_BY_CONCEPT_ID`: adjacency for traversal; respects
  directional vs symmetric types from `relations.py`.

### Representation-layer hydration

**Where does the back-reference data go?** The phase-2 models are deliberately
thin and these fields **do not exist yet**: today `Lemma` has no `.senses`,
`Concept` has no `.senses`/`.lemmas`, and `Sense` has no `.lemma`/`.concept`
(only the id fields). This phase **adds** them to the phase-2 models as new,
non-persisted, store-populated fields - that is their home:

- `lemma.py` (`Lemma`): add `senses: list[Sense] | None` and
  `concepts: list[Concept] | None` (field spec
  `Field(default=None, exclude=True, repr=False)`).
- `concept.py` (`Concept`): add `senses: list[Sense] | None` (same field spec)
  and a `lemmas` view (per-language grouping derived from `senses`; a property or
  a hydrated dict `dict[str, list[Lemma]]`, not a stored field).
- `sense.py` (`Sense`): add `lemma: Lemma | None` and `concept: Concept | None`
  (same field spec).

**`Lemma.concepts` is included** (revising the earlier "no concepts field"
stance): the drift argument that removed it from the *persisted* shape in phase 2
does not apply to a **hydrated, `exclude=True`** field - it is never written, so
it cannot disagree with the sense table on disk. The store derives it once at
hydration from the lemma's senses (`[s.concept for s in lemma.senses]`,
de-duplicated), giving callers the convenient `lemma.concepts` directly while the
sense table stays the single persisted source of truth.

Mechanics:

- `exclude=True` keeps every one of these out of `model_dump()`, so the persisted
  Parquet shape (and the phase-2 round-trip tests) is unaffected. `default=None`
  (not `default_factory=list`) lets the guard distinguish "never hydrated" from
  "hydrated, genuinely empty".
- **Circular references** (`Sense` <-> `Lemma`/`Concept`) need care: per the
  pydantic v2 docs, `model_rebuild()` builds the whole core schema and **all
  referenced types must be present in the runtime namespace at the point it is
  called** - a `TYPE_CHECKING`-only import is *not* enough (it satisfies the
  string annotation and the linter, but the class object does not exist at
  runtime, so the rebuild cannot resolve it). The pattern:
    1. In each model module keep the forward-ref annotations as strings (the
       `from __future__ import annotations` already in place does this); a
       `TYPE_CHECKING` import is fine purely to satisfy type-checkers.
    2. In **one central module that really imports all three model classes at
       runtime** (e.g. `lexicon/__init__.py` or the store module), call
       `Lemma.model_rebuild()`, `Concept.model_rebuild()`, `Sense.model_rebuild()`
       after the imports so every referenced class is in scope. (If a stray
       forward ref still fails to resolve, pass it explicitly via
       `model_rebuild(_types_namespace={...})`.)
  This keeps the model modules import-cycle-free at load while giving the rebuild
  site the concrete classes it requires.
- The store is the **single owner**: it sets these fields. In resident mode it
  does so once for the whole graph after all registries are loaded, in a
  `_hydrate()` pass; in SQLite mode it does so per object at fetch time (below).
- **Unhydrated-object guard** (carried from phase 2): a `Sense` built ad hoc
  (ingestion before registries exist, or a unit test) has `sense.lemma is None`.
  Decision for this phase: the accessor raises a clear **`SenseNotHydratedError`**
  rather than returning `None` silently; the persisted `lemma_id` / `concept_id`
  remain the always-available fallback path. (Lazy resolution through the store
  was considered but rejected: it couples the model module to the store and hides
  the "you forgot to load" bug instead of surfacing it.) The same guard policy
  applies to `Lemma.senses` / `Concept.senses`.

**Eager vs on-demand hydration (why SQLite mode can still hydrate).** Hydration is
nothing more than *calling the query methods and attaching the result to the
object's fields* - so yes, SQLite mode can hydrate too, just at a different time
and scope:

- **Resident mode - eager, whole-graph:** wire every object to every other once at
  load. Cheap (in-memory), and the references are **shared instances**
  (`sense.concept is _CONCEPTS_BY_ID[id]`).
- **SQLite mode - on-demand, per fetch:** when `get_lemma_by_id` returns a lemma,
  populate *that* lemma's `.senses` / `.concepts` right then by running the
  adjacency queries (your suggestion). Only the objects actually touched get
  materialised, so the ~0-resident benefit is kept.

The on-demand path has three constraints the plan must respect, which is why it is
**bounded and opt-in**, not automatic:

- **Depth must be bounded.** Hydrating `lemma -> senses -> concepts -> their
  senses -> their lemmas -> ...` walks transitively across the whole graph (and
  loops on the `lemma <-> sense` back-edge). So on-demand hydration fills **one or
  two hops** and leaves deeper links unhydrated (the `SenseNotHydratedError` guard
  marks the boundary); it never recurses the cycle.
- **Cost is per fetch.** Each hydrated object costs N extra indexed queries
  (~30 us each). Fine for a point lookup; wasteful when a filter returns hundreds
  of lemmas. So hydration is **opt-in per call** (e.g. `get_lemma_by_id(id, *,
  hydrate=False)`), defaulting off for bulk/filtered reads.
- **No identity guarantee.** Fresh fetches create new instances, so the same
  concept reached two ways is two objects (unlike resident mode's shared
  instances) - read-only access makes this harmless, but it is a real difference.

So the rule is timing + scope, not capability: resident mode hydrates everything
once; SQLite mode hydrates shallowly, per object, on request - both through the
same store methods. Callers that want neither just call the methods directly.

**Fallback if hydration proves messy.** Hydrated model fields are the *preferred*
outcome - having `lemma.senses` / `lemma.concepts` / `sense.concept` ready on the
object is the nicest ergonomics. But if the circular-ref rebuild, the
guard/`None` handling, or the dual-mode behaviour turns fragile, the escape hatch
is to **drop the back-ref fields entirely and keep navigation in the store**: the
query methods (`senses_for_lemma`, `concepts_for_lemma`, `lemmas_for_concept`,
...) plus small **helper functions** for the common walks (e.g.
`concepts_for_lemma` = senses -> concepts) already cover every access pattern and
are mode-agnostic. This is a clean, fully-specified fallback, not a degraded one;
the only loss is the convenience of reaching the graph through attributes instead
of function calls. The models stay thin and the store owns all traversal.

### Query helpers

- Implement the full surface in the table above. `get_false_friends_for_lemma`
  returns each match as `(other_lemma, edge)` (resolving the non-self endpoint),
  mirroring the brainstorm sketch.
- These are the stable surface `lang-tutor` and the webapp consume; keep
  signatures additive so consumers migrate in phase 9.

### Webapp endpoints

- Extend `webapp/routers/lemmas_router.py` (lemma payload stays lean) and add
  concept/relation read endpoints so the heavy graph is fetched only when needed
  (e.g. building a vocabulary-trap exercise), not bundled into every lemma
  response.

### Loader robustness

- Clear, named errors on malformed rows (a `MalformedRecordError`-style
  exception rather than bare `ValueError`).
- Colliding concept slugs: detected and flagged at load (the `hash[:12]` suffix
  already keeps ids unique; readability disambiguation is an ingestion concern in
  phase 5, but the store warns on collisions so they are visible).

### Dependencies

- `pyarrow` (codec) and `duckdb` (inspect path) move from the phase-3 scratch
  venv install into `pyproject.toml`. Prefer an **optional extra** (e.g.
  `lexicon`/`store`) over a core dep, since `lang-tutor` consumes only the lemma
  read surface and need not pull a columnar engine; the webapp/store extra
  depends on it.

### Tests (`tests/lexicon/`, `tests/webapp/`)

- **Codec round-trip:** a fixture table dumped to Parquet and reloaded is
  equal model-for-model; nested columns (`examples`, `topics`, `definitions`
  map) survive; `model_dump()` is byte-stable (no computed/back-ref fields).
- Index correctness over a small fixture: sense adjacency both directions,
  false-friend symmetry (one stored edge appears under both endpoints), concept
  relation directional vs symmetric traversal.
- Hydration: after load, `sense.lemma` / `lemma.senses` / `concept.lemmas`
  resolve; `model_dump()` still carries no back-refs; an unhydrated `Sense`
  accessor raises `SenseNotHydratedError`; `model_rebuild()` resolves the forward
  refs without an import cycle.
- **Inspect/edit:** `export_table` -> edit -> `import_table` round-trips and a
  malformed edited row raises a clear validation error before any write.
- Missing-id edge cases return empty / `None` as specified, never raise.

## Sequencing with phase 3

Planned in lockstep with phase 3, executed staged:

1. **Now (planning):** this query surface + access-pattern list is fixed; it is
   phase 3's benchmark target.
2. **Phase 3 execution:** experiments measure *these* patterns (id lookups, sense
   adjacency, false-friend fan-out) per candidate format, writing the
   (de)serialization against the **codec seam** above - throwaway harness, but a
   reusable codec.
3. **Phase 3 decision:** format + access engine chosen with numbers.
4. **Phase 4 execution:** implement the store against the decision, promoting the
   winning codec.

**Phase 3 is now done** (status `done`): the decision is Parquet+zstd under LFS,
resident dicts for the sample / SQLite point lookups for the full corpus, DuckDB
for inspect only - folded into "Phase 3 inputs (decided)" above. So step 4 is
unblocked.

The store implementation deliberately did **not** start before phase 3 decided,
so it is never built on an unvalidated format. See the mirrored note in
[`03_storage_indexing.md`](03_storage_indexing.md).

## lang-tutor status

Phase 2 already dropped fields `lang-tutor` reads (`translations`, `frequency`,
`glosses`), so `lang-tutor` stays red until its consumer uplift in **phase 9**.
This phase keeps the lemma read surface stable and additive so that uplift is
mechanical, but does not itself un-break `lang-tutor` (no concept/sense data
exists for it to consume until phase 5/9).

## Out of scope

- Producing the data files (phase 5); frequency/CEFR values (phase 6) and
  relation contents (phase 7) - plumbing only.
- The storage-format decision itself (phase 3); this phase consumes it.
- The `lang-tutor` consumer uplift and sample-data regeneration (phase 9).

## Done when

- The codec seam reads/writes **Parquet (zstd)** (per-language for
  `senses`/`lemmas`); `_load_table`/`_dump_table` round-trip the fixture
  model-for-model with nested columns intact.
- The full query surface is implemented and indexed in **resident mode**;
  hydration adds the `Lemma.senses` / `Concept.senses`+`lemmas` / `Sense.lemma`
  /`Sense.concept` back-ref fields and populates them with the
  `SenseNotHydratedError` guard in place; `model_rebuild()` resolves the forward
  refs cleanly.
- The **SQLite-mode seam** is specified and the query-method parity is testable
  (engine swap behind the same surface), even if the indexed implementation lands
  with phase-5 data.
- `inspect_table` and the `export_table`/`import_table` round-trip work over the
  Parquet, driven from a notebook under the new `notebooks/` folder (thin caller,
  no logic); `pyarrow`/`duckdb` are declared in `pyproject.toml` (extra).
- Concept/relation read endpoints exist; the lemma payload stays lean.
- Tests cover codec round-trip, indexing, symmetry, hydration, inspect/edit, and
  missing-id edge cases over a fixture dataset.
- `uv run pytest && uv run ruff check . && uv run pyright` passes in `lang-tools`.
- Docs updated (`docs/library/lexicon.md` gains a store/query + inspect/edit
  section); the tracking Log records the phase.
