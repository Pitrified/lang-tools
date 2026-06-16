# concept model - implementation tracking

Uplift of `lang_tools.lexicon` (renamed from `lang_tools.words` in phase 1) from a
flat `Lemma` to a concept-centric lexical model (thin `Lemma`,
language-independent `Concept`/synset, explicit `Sense` edge, and decoupled
relation edge tables), plus an open-source multilingual dataset built on OMW.
Full analysis and decisions in
[`00-concepts-brainstorm.md`](00-concepts-brainstorm.md).

Status: phase 1 fully planned; phases 2-10 are draft scope sketches (~1 page
each) to hold the overarching story. Phases are intentionally easy to merge or
split as the design firms up.

## Key decisions (cross-cutting)

- **No data migration.** The ~50 bootstrap lemmas are disposable sample data and
  `lang-tutor` only consumes a lemma list; replace the model and regenerate fresh
  sample data instead of backfilling.
- **`lang-tutor` moves in lockstep.** It is ours, so there is no external
  contract to freeze - we rename/reshape and update the consumer in the same
  change. It still only needs `text` / `language` / `part_of_speech`.
- **Rename `Word` -> `Lemma`** (literature term). Done as the preliminary phase 1
  so all later phases are written in the target vocabulary. Pro/con in the
  brainstorm.
- **OMW (Apache-2.0) is the concept backbone**, Wiktionary is enrichment-only,
  LLM does mapping/granularity only - not as a primary data source.
- **Dataset ships free and open source.** Core stays permissive; CC-BY-SA
  Wiktionary handling is an open question.
- **Concept ids: `c__{slug}__{hash[:12]}`** (readable slug + hash safety net).
- **Frequency and CEFR complexity are properties of the sense, not the token**
  (the "bank" polysemy trap), both living on an explicit `Sense` edge.
- **Parquet tables are the source of truth.** Edits update the Parquet directly
  (phase-4 corpus round-trip); no committed patch/overlay layer. A future
  re-ingestion of updated OMW/kaikki is a *smart merge* against the curated Parquet,
  using a per-row `source` tag - deferred (phase 5 only guarantees the machine
  baseline is rebuildable from a pinned manifest).
- **SQLite-only runtime.** The resident-dict mode is removed; one SQLite engine
  serves the whole query surface (phase 4.1, before phase 5). Supersedes phase 4's
  resident/SQLite dual-mode + `_hydrate`/`LexiconStoreMode` seam.
- **Single load path: the store reads Parquet only** (phase 4.2). `from_data_fol`
  reads `data/lexicon/` Parquet and raises `CorpusNotFoundError` when absent - no
  JSONL-seed fallback. The committed `data/bootstrap/*.jsonl` seed is a dev
  **input**, parquetized into the sample corpus by `parquetize_seed.ipynb`.
  Consequently `pyarrow` is a base dependency (`duckdb` stays the inspect-only
  `store` extra), and the default store builds lazily on first `get_store()`.

## Phases (proposed)

| #  | Phase                         | Plan                                                     | Status | One-liner                                                                                                              |
| -- | ----------------------------- | -------------------------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------- |
| 1  | Rename `Word` -> `Lemma`      | [`01_rename_word_to_lemma.md`](01_rename_word_to_lemma.md) | done | Preliminary mechanical refactor `Word`->`Lemma` (and `lang-tutor`) so later phases use literature vocabulary.          |
| 2  | Core data models              | [`02_core_models.md`](02_core_models.md)                 | done | Define thin `Lemma`, `Concept`, explicit `Sense` edge, `FalseFriendRelation`, generic relation edge; concept id scheme. |
| 3  | Storage & indexing analysis   | [`03_storage_indexing.md`](03_storage_indexing.md)       | done | Two-axis (storage format x access engine) analysis: ship Parquet under LFS, query via dicts/SQLite/DuckDB; decided by measured numbers. |
| 4  | Store layer + indexes         | [`04_store_layer.md`](04_store_layer.md)                 | done | Extend `lemma_store` with concept/sense/edge registries, look-aside indexes, and back-ref hydration; query surface feeds phase 3. |
| 4.1 | SQLite-only runtime engine   | [`04.1_sqlite_mode.md`](04.1_sqlite_mode.md)             | done   | Collapse the store to a single SQLite engine and remove resident mode; sequenced before phase 5 so the engine is settled. Supersedes phase 4's dual-mode. |
| 4.2 | Single load path (Parquet-only) | [`04.2_seed_data.md`](04.2_seed_data.md)              | done   | Remove the JSONL-seed loader + pyarrow-missing fallback; the store reads Parquet only. Seed becomes a dev input parquetized by a notebook. pyarrow -> base dep. |
| 5  | Initial ingestion pipeline    | [`05_ingestion.md`](05_ingestion.md)                     | done | One-time initial build: OMW via `wn` -> concepts, kaikki enrichment, optional LLM granularity. Parquet is the source of truth; re-ingestion merge deferred. |
| 6  | Frequency & complexity        | [`06_frequency_complexity.md`](06_frequency_complexity.md) | draft  | Per-sense token/sense frequency (`wordfreq`, sense-tag weights) and CEFR complexity (graded lists / estimated).        |
| 7  | Semantic relations            | [`07_relations.md`](07_relations.md)                     | draft  | Ingest hypernymy/hyponymy and antonymy as typed edges from OMW.                                                        |
| 8  | Maintenance (LLM-based)       | [`08_maintenance.md`](08_maintenance.md)                 | draft  | LLM-assisted upkeep: new lemma->concept mapping, gloss enrichment, slug dedup, validation against OMW.                 |
| 9  | Sample data + consumer uplift | [`09_sample_and_consumer.md`](09_sample_and_consumer.md) | draft  | Regenerate fresh sample data from the pipeline; point `lemma_store` and `lang-tutor` at it.                            |
| 10 | Licensing & packaging         | [`10_licensing_docs.md`](10_licensing_docs.md)           | draft  | Finalize open license, source attribution / dataset card, and docs.                                                    |

Status values: draft / planned / in progress / done / superseded / discarded.

Likely merge/split points as we iterate:

- Phase 6 (frequency & complexity) may fold into 5 (ingestion) or 2 (models)
  depending on the `Sense`-edge decision; frequency and CEFR complexity share the
  same per-sense home so they stay one phase.
- Phase 7 (relations) may fold into 5 (ingestion) since OMW supplies the edges.
- Phase 3 (storage analysis) gates 4 and 5 and may reshape the model in 2.
  Phases 3 and 4 are planned in lockstep but executed staged: phase 4's query
  surface is phase 3's benchmark target, and phase 3's format decision gates
  phase 4's implementation (see both sub-plans' "Sequencing" sections).

## Log

Append-only. Newest at the bottom.

- 2026-06-15 : bootstrapped the plan folder from the existing brainstorm; folded
  the open points (word frequency, no-migration uplift, git-LFS storage analysis,
  open license, semantic relations) into `00-concepts-brainstorm.md`; drafted the
  9 proposed phases here as one-liners (sub-plan files not yet written).
- 2026-06-15 : per review - lang-tutor moves in lockstep (no contract to freeze);
  added preliminary phase 0 (rename `Word` -> `Lemma`) with pro/con assessment in
  the brainstorm; renamed `Word` -> `Lemma` across phase descriptions.
- 2026-06-15 : green-lit the rename and applied it coherently (class, ids, store
  internals, module paths); package named `lang_tools.lexicon` (holds the whole
  lexical graph, not just lemmas). Added a "Lemma complexity (CEFR level)"
  section - per-sense like frequency, stored on the `Sense` edge; folded into
  the frequency phase (now "Frequency & complexity").
- 2026-06-15 : renumbered phases to 1-10 (rename is now phase 1, no phase 0);
  earlier log lines that say "phase 0"/"phase 5" refer to the pre-renumber
  scheme. Brainstorm forward-references updated to "phase 1".
- 2026-06-15 : created all 10 sub-plan files; fully fleshed phase 1 (status
  planned, grounded in the real `lang_tools.words` -> `lang_tools.lexicon` rename
  across both repos incl. the HTTP surface); phases 2-10 written as ~1-page draft
  scope sketches.
- 2026-06-16 : executed phase 1 (status done). lang-tools: package
  `lang_tools.words` -> `lang_tools.lexicon`; modules `word/word_id/word_store` ->
  `lemma/lemma_id/lemma_store`; `Word`/`WordExample`/`word_id` and all store +
  ingestion helpers renamed; webapp router -> `lemmas_router` serving
  `/api/v1/lemmas`; per the flagged decision, also renamed `word_generator` ->
  `lemma_generator` (module, classes, prompt folder, `num_words` -> `num_lemmas`).
  lang-tutor (lockstep, editable path dep): `Word` -> `Lemma`, content source
  methods `get_lemmas_filtered`/`get_lemma_by_id`, `_LEMMAS_PATH` ->
  `/api/v1/lemmas`, internal models `UserWordProgress` -> `UserLemmaProgress`,
  `WordFilter` -> `LemmaFilter`, `select_words` -> `select_lemmas`, `WordResult`
  -> `LemmaResult` (field `word_id` -> `lemma_id`), page router -> `lemmas_router`
  (`/lemmas`). Exercise JSON API keys also renamed for coherence
  (`num_words`->`num_lemmas`, `left_words`/`right_words`->`left_lemmas`/`right_lemmas`);
  only `Wordle` game vocabulary (`word_length`, `WordleConfig`) intentionally
  kept. Docs
  updated in both repos (`words.md` -> `lexicon.md`, guides, mkdocs nav). Both
  suites green: lang-tools 69 passed, lang-tutor 123 passed; ruff + pyright clean
  in both. Grep for `Word`/`word_id`/`word_store`/`lang_tools.words` is clean
  across src/tests/docs in both repos.
- 2026-06-16 : fleshed phase 2 into a plan of record (status planned), grounded in
  the real `lang_tools.lexicon` files. Scoped it to models + id helpers + unit
  tests, with minimal call-site updates to keep the suite green; store registries
  (phase 4), ingestion (phase 5), and frequency/CEFR/relation population
  (phases 6-7) stay out. Resolved the open points as recommendations to confirm:
  promote `Sense` as the single source of truth and drop `Lemma.concept_ids`
  (supersedes the sketch's "add concept_ids"); canonical glosses move to
  `Concept.definitions` (raw source glosses deferred to phase 5); `concept_id`
  takes a pre-computed slug so slug-source choice stays in ingestion.
- 2026-06-16 : confirmed the explicit `Sense` edge (richer per-sense metadata
  earns it) and iterated phase 2 on the persistence-vs-representation split.
  Analyzed `Concept.lemmas` as redundant once `Sense` exists (rebuildable from the
  sense set + each lemma's language) and dropped it from the persisted shape, same
  reasoning as decoupling false friends. Persisted models stay thin/id-only and
  drift-free; convenience navigation (`sense.lemma`, `sense.concept`,
  `lemma.senses`, computed `concept.lemmas`) becomes a representation-layer concern
  built in phase 4 via store-hydrated `exclude=True` fields (alternatives - lazy
  store properties, separate view classes - considered and noted).
- 2026-06-16 : accepted phase 2's two remaining open points - glosses move entirely
  to `Concept.definitions` (none on `Lemma`); concept slug from OMW/ILI key first,
  else English gloss. All phase 2 model decisions now confirmed. Noted the
  unhydrated-`Sense` guard (accessor raises vs lazy-resolves rather than returning
  `None`) in the phase 4 draft. Folded the `Sense` promotion, dropped
  `Lemma.concept_ids` / `Concept.lemmas`, persistence-vs-representation split, and
  gloss decision back into `00-concepts-brainstorm.md` (model sections + Resolved
  list) so the high-level track stays aligned.
- 2026-06-16 : executed phase 2 (status done). New modules in
  `src/lang_tools/lexicon/`: `concept.py` (`Concept` = id + `definitions`, id-shape
  validator), `sense.py` (`Sense` edge with per-sense frequency/CEFR fields +
  computed id), `relations.py` (`FalseFriendRelation` canonical `a<b`,
  `ConceptRelation` stub with `SYMMETRIC_CONCEPT_RELATIONS`, both reject self-edges
  via `SelfRelationError`), `concept_id.py` (`c__{slug}__{hash[:12]}`,
  `CONCEPT_ID_RE`, `EmptyConceptSlugError`), `sense_id.py` (16-hex over the ordered
  endpoint pair). Reshaped `lemma.py` to the thin token (dropped
  `translations`/`frequency`/`FrequencyLevel`/`glosses`/`Gloss`/`GlossExample`/
  `false_friends`/`FalseFriend`); kept `LemmaExample`. Updated ingestion
  (`csv_loader`, `dedup`, `wiktionary`) to build the thin `Lemma` and ignore legacy
  columns; `__init__` exports the new surface. New tests: `test_concept_id`,
  `test_sense_id`, `test_sense`, `test_concept`, `test_relations`; updated
  `test_lemma`/`test_csv_loader`/`test_dedup`. lang-tools green: 92 passed, ruff +
  pyright clean. Docs refreshed (`docs/library/lexicon.md`, `frozen_api.md`).
  Note: `lang-tutor` still reads the dropped fields (`translations`/`frequency`/
  `glosses`) and is therefore red until its consumer uplift in phase 9 - this is
  the deliberate phase-2 scope boundary (no store/concept data exists to migrate it
  onto yet).
- 2026-06-16 : fleshed phase 3 into a plan of record (status planned) after a web
  survey (DuckDB, Parquet, SQLite, git-LFS/DVC). Key reframing: storage format and
  query engine are separable axes - DuckDB queries CSV/JSONL/Parquet directly, so
  we can keep LFS-friendly files and still get SQL on top without committing a DB
  blob. Surveyed both axes in tables with cited sources; flagged that git LFS does
  not delta-compress (so JSONL's diff benefit only pays off in *normal* git, making
  the size measurement the pivot), that DuckDB's native `.duckdb` format is
  version-unstable (official remedy is export-to-Parquet, so do not ship it), and
  that `wn` already stores OMW in SQLite. Provisional recommendation: ship Parquet
  partitioned per table/language under LFS, keep a JSONL export for inspection,
  runtime stays in-memory dicts (promote hot tables to SQLite point lookups only if
  measured memory/latency demands). Refines the brainstorm's CSV/JSONL-vs-SQLite
  lean; the executed phase will confirm/overturn with measured numbers and fold the
  memo back into the brainstorm.
- 2026-06-16 : fleshed phase 4 into a plan of record (status planned) and resolved
  the phase 3/4 sequencing question (plan in lockstep, execute staged). Led the
  plan with the read/query surface + access-pattern table (point lookups + bounded
  adjacency joins, not aggregations) so it doubles as phase 3's benchmark target.
  Introduced a codec seam (`_load_table`/`_dump_table`) so phase 3's experiment
  serializers promote into the real loader instead of being throwaway. Specified
  the back-ref hydration (store-owned `_hydrate()` pass over the phase-2
  `exclude=True` fields) and resolved the unhydrated-`Sense` guard: accessor raises
  `SenseNotHydratedError` (lazy store resolution considered and rejected for
  coupling/bug-hiding); `lemma_id`/`concept_id` stay the fallback. Added concept/
  relation read endpoints (lean lemma payload kept). Mirrored a "Sequencing with
  phase 4" note into `03_storage_indexing.md`; phase-4 implementation deliberately
  waits on phase 3's format decision. lang-tutor stays red until phase 9.
- 2026-06-16 : executed phase 3 (status done) - ran the storage/indexing
  experiments in
  `scratch_space/09_concept_model/03_storage_indexing/03.1_performance_tests.ipynb`
  over a synthetic corpus at the OMW 5-language scale (400k lemmas, 100k concepts,
  1M senses, 50k false-friend + 200k concept-relation edges), serializing each
  table to JSONL/JSONL.gz/CSV/Parquet(snappy,zstd)/SQLite and timing the phase-4
  query surface across in-memory dicts, indexed SQLite, and DuckDB-over-Parquet.
  Measured: Parquet+zstd ~8.6x smaller than JSONL (40.9 vs 350.3 MB total); as
  JSONL the senses table (227 MB) exceeds GitHub's 100 MB hard limit so the big
  tables need LFS regardless; full graph as pydantic dicts ~1.9 GB resident;
  point lookups dict ~3 us / SQLite ~30 us / DuckDB ~16 ms; raw filter/adjacency
  scans ~150 ms (need explicit indexes). Decision (confirms+sharpens the
  provisional lean): ship Parquet+zstd partitioned per table/language under LFS;
  keep small curated tables as JSONL in normal git; runtime stays in-memory dicts
  for the sample but promotes hot tables to SQLite point lookups for the full
  corpus (measured trigger, not "maybe later"); DuckDB is a build/QA reader only;
  do not ship a .duckdb/.sqlite as canonical. Decision memo + drafted
  `.gitattributes`/partitioning folded into `03_storage_indexing.md` and the
  Storage section of `00-concepts-brainstorm.md`. Scratch deps `pyarrow`+`duckdb`
  installed into the venv (not added to pyproject).
- 2026-06-16 : per review - refined the phase-3 storage decision to ship *all*
  tables (including the small curated `false_friends`/`concept_relations`) as
  Parquet under LFS for uniformity, overturning the "small tables as JSONL in
  normal git" point: a 50k-row textual diff is not meaningfully reviewable and a
  model change rewrites every line, so line-diffability is a false comfort and a
  single distribution path avoids special cases. Replaced the lost human-readable
  artifact with an explicit inspect/edit workflow (DuckDB SQL + a thin `inspect`
  CLI for reading; `export_table`->edit JSONL->`import_table` with pydantic
  validation for edits; schema changes regenerate from ingestion, not line
  patches). Updated the memo in `03_storage_indexing.md` (gitattributes now one
  `data/lexicon/**/*.parquet` rule), the brainstorm Storage section, and the
  notebook decision-memo cell.
- 2026-06-16 : reviewed and expanded the phase 4 plan with phase-3 learnings
  (still planned). Added a "Phase 3 inputs (decided)" section (Parquet+zstd under
  LFS, two-tier runtime, DuckDB inspect-only, indexes mandatory, deps to
  pyproject); made the codec seam Parquet-specific (nested pyarrow schemas,
  per-language partitioning) and added the inspect/edit tooling (`inspect` CLI +
  `export_table`/`import_table`). Added a "Runtime modes (dict vs SQLite)"
  subsection tying the ~1.9 GB resident finding to a resident-mode (sample) vs
  SQLite-mode (full corpus) engine swap behind one query surface. Answered the
  open hydration question: the back-ref fields do **not** exist on the current
  thin models - phase 4 adds `Lemma.senses`, `Concept.senses` (+`lemmas` view),
  `Sense.lemma`/`Sense.concept` as `exclude=True` store-populated fields (no
  `Lemma.concepts`; concepts reached via senses), resolving the `Sense`<->`Lemma`
  cycle with `TYPE_CHECKING` + `model_rebuild()`; hydration is resident-mode only,
  SQLite mode uses store query methods. Expanded Tests/Done-when accordingly.
- 2026-06-16 : per review, four refinements to the phase 4 plan. (1) Dropped the
  `inspect` CLI; corpus interaction is now a thin notebook under a new general
  top-level `notebooks/` folder (distinct from `scratch_space/`) calling package
  functions (`inspect_table`, `export_table`/`import_table`) - no logic in the
  notebook. (2) Reinstated `Lemma.concepts` as a hydrated `exclude=True` field:
  the phase-2 drift argument applies only to the *persisted* shape, and a hydrated
  (never-written) back-ref cannot drift, so it is safe and convenient (derived
  from senses at hydration). (3) Corrected the circular-ref mechanics after
  checking the pydantic v2 docs: `model_rebuild()` needs the referenced classes in
  the *runtime* namespace, so a TYPE_CHECKING-only import is insufficient - the
  rebuild must run in a module that really imports all three model classes (forward
  refs stay strings; `_types_namespace` as a last resort). (4) Documented an
  explicit fallback: if hydration is fragile, drop the back-ref fields and keep
  navigation in store query methods + helpers (clean, mode-agnostic, fully
  specified), with hydrated fields the preferred-but-optional ergonomics.
- 2026-06-16 : executed phase 4 (status done). New modules in
  `src/lang_tools/lexicon/`: `codec.py` (Parquet/zstd seam `_load_table`/
  `_dump_table` over the phase-3 pyarrow schemas, lazy `pyarrow` import so the
  `store` extra stays optional, per-language partitioning for `lemmas`/`senses`,
  `MalformedRecordError`/`UnknownTableError`/`StoreDependencyMissingError`);
  `hydration.py` (`NotHydratedError`/`SenseNotHydratedError` + a `require` guard
  helper); `corpus.py` (`inspect_table` via DuckDB, `export_table`/`import_table`
  validated JSONL round-trip). Reshaped the models: added the `exclude=True`
  store-hydrated back-refs (`Lemma.senses`/`Lemma.concepts`,
  `Concept.senses`/`Concept.lemmas`, `Sense.lemma`/`Sense.concept`) with
  `resolve_*` guard accessors; circular refs resolved via `model_rebuild()` in
  the store module (parent-namespace pickup, not TYPE_CHECKING-only - confirmed
  the runtime-namespace requirement). Generalised `lemma_store.py` into
  `LexiconStore` (registries, look-aside indexes incl. both-endpoint false-friend
  and concept-relation indexing, eager `_hydrate()`, slug-collision warning, the
  full query surface) with a `LexiconStoreMode` resident/SQLite seam (SQLite
  raises `SqliteModeNotImplementedError` until phase-5 data) and a default store +
  delegating module helpers; lemmas still load from the bootstrap CSV sample
  (keeps the webapp lemma API green), concept/sense/edge tables load from Parquet
  (empty until phase 5). Webapp: new `concepts_router` (concept fetch + relations)
  registered in `main`/conftest; false-friends endpoint on `lemmas_router`.
  Notebook `notebooks/lexicon_corpus/explore.ipynb` (thin caller). Deps: `pyarrow`
  + `duckdb` graduated to a `store` optional extra in `pyproject.toml`. Tests:
  `test_codec`, `test_lexicon_store`, `test_corpus`, `test_concepts_api` (codec
  round-trip incl. nested/map columns + lean dump, indexing both directions,
  false-friend symmetry, directional-vs-symmetric concept relations, hydration +
  unhydrated-guard, inspect/edit round-trip + malformed-row rejection, missing-id
  empties, SQLite-mode error). Relaxed `*.ipynb` ruff per-file-ignores (ANN/D/
  S101/S608/E402/I001/PLR2004/PLW0108) so exploratory notebooks pass `ruff check
  .`. Docs: `docs/library/lexicon.md` gained store/query + hydration + storage +
  inspect/edit sections; `frozen_api.md` lists the new surface. Suite green:
  119 passed, ruff clean, pyright 0 errors. `data/**` is already LFS-tracked, so
  the drafted `data/lexicon/**/*.parquet` rule needs no `.gitattributes` change.
  lang-tutor stays red until phase 9 (deliberate).
- 2026-06-16 : per review, corrected the SQLite-mode hydration claim. Hydration is
  just "call the query methods and attach the result", so SQLite mode *can*
  hydrate - the real split is timing/scope: resident mode hydrates the whole graph
  eagerly at load (shared instances); SQLite mode hydrates per object on demand at
  fetch time, but **bounded** (1-2 hops, guard marks the edge - the lemma<->sense
  cycle would otherwise walk the whole graph), **opt-in per call** (each fetch
  costs N ~30 us queries; default off for bulk/filtered reads), and with **no
  shared-instance identity**. Updated the Runtime-modes and Hydration sections.
- 2026-06-16 : fleshed phase 5 into a plan of record (status planned). Reframed the
  phase around the real hard part - **separating a deterministic re-runnable build
  from durable manual curation** - not OMW parsing. Architecture: three pure stages
  (acquire -> build -> overlay) over two layers - a disposable generated base
  (`data/lexicon/_base/`, byte-identical from pinned raw inputs) and a committed
  curated overlay (`data/lexicon/_overlay/*.jsonl`, field-level patches keyed by
  id). Shipped Parquet = base + overlay merge, fully reproducible from
  `(raw, build code, overlay)`. Provenance carried as extra Parquet columns
  (`source`/`source_ref`/`build_version`, source enum omw|kaikki|llm|manual) added
  to `_DROP_ON_LOAD` so models stay thin; a `_build.json` manifest pins wn/ILI +
  kaikki versions. This answers the user's "idempotency fails" worry: in-place
  mutation is designed out (base never hand-edited, curation is an *input*), so a
  rare full rebuild reproduces the shipped tables with hand edits reapplied - and
  it is the clean seam to phase 8 (phase 5 builds base + overlay mechanism, phase 8
  writes overlay entries, never the base). Module layout extends `ingestion/`
  (`provenance`/`acquire`/`sources/{omw,kaikki}`/`build`/`overlay`/`pipeline`),
  reusing `wiktionary.py`/`dedup.py`; `wn` new lazy dep. Two thin driver notebooks
  under `notebooks/lexicon_ingest/` (01 download, 02 build); answered the notebook
  question - the existing `explore` notebook starts working once build writes
  Parquet and inspects fine at full scale (DuckDB-over-Parquet, not resident); the
  size worry only hits resident-mode store load (the phase-4 SQLite-mode trigger),
  and phase 5 ships only a sample slice. LLM granularity collapse kept as an
  optional seam, not a "done" requirement. Open points flagged for the user:
  overlay representation, committed output (sample vs full), LLM collapse placement.
- 2026-06-16 : per review, reshaped phase 5 - dropped the committed base/overlay/
  provenance-patch architecture (rejected: an LLM-driven curation stream could grow
  to ~100k patch lines, and "regenerate examples" edits do not belong in a patch
  file). New model: the **Parquet tables are the source of truth**; phase 5 is a
  one-time initial build (acquire -> transform -> write Parquet + committed sample
  slice), and subsequent edits update the Parquet directly via the phase-4 corpus
  round-trip. A future re-ingestion of updated OMW/kaikki becomes a **smart merge**
  against the curated Parquet - genuinely the hard part, but rare and not needed
  for the initial build, so **deferred** (own later phase or folded into phase 8).
  Kept one lightweight `source` provenance column (`omw|kaikki|llm|manual`, in
  `_DROP_ON_LOAD` so models stay thin) + a `_build.json` version manifest as the
  only seam the deferred merge needs. LLM granularity collapse stays an optional
  seam (confirmed). Committed output decided: create+commit a sample slice now.
  Added phase 5.1 (status draft) for the SQLite runtime mode - ingest the
  source-of-truth Parquet into SQLite and serve the phase-4 query surface from it,
  with an explicit optional assessment of dropping the in-memory resident mode
  entirely (the double mode is awkward). Next: brainstorm the deferred-merge
  mechanics and the resident-vs-SQLite-only question before either becomes execution
  -ready.
- 2026-06-16 : resolved both brainstorm threads. (Q1, merge baseline) decision B -
  do not commit a base snapshot; the `_build.json` manifest pins source versions and
  the transform is deterministic, so the machine baseline is *reconstructible* from
  the regenerable raw cache; 2-way-vs-3-way merge deferred. Folded into 05's
  provenance section. (Q2, runtime) committed to **SQLite-only** - remove resident
  mode outright. Decided to do the engine swap **before** phase 5: renamed
  `05.1_sqlite_mode.md` -> `04.1_sqlite_mode.md` (status planned), reframed from
  "add SQLite mode / maybe drop resident" to "collapse to one SQLite engine, delete
  resident + `_hydrate`/`LexiconStoreMode`/`SqliteModeNotImplementedError`".
  Rationale: under SQLite-only those are dead code, so settling the engine first
  means phase 5 is written once against the final engine, not reworked. Recorded the
  one consequence as 4.1's open point: removing resident also removes the
  bootstrap-CSV->dict path that keeps the webapp lemma API green, so 4.1 must
  convert bootstrap CSV -> sample Parquet -> SQLite (recommended, non-throwaway) or
  let the webapp lemma API go red until phase 5. Added two cross-cutting key
  decisions (Parquet-as-source-of-truth, SQLite-only). Phase 5 now depends on 4.1.
- 2026-06-16 : resolved 4.1's bootstrap-data-source open point - keep the webapp
  green via a small **hand-authored sample**, authored now (the id constructors +
  models + codec already exist; no OMW needed for a handful). Pipeline reuses
  existing machinery: committed sample **JSONL** seed -> `import_table`
  (JSONL->Parquet round-trip) -> sample Parquet -> build SQLite. Format is JSONL not
  CSV (nested `Concept.definitions`/`Lemma` examples don't fit CSV; ~50-row sample
  is diffable in normal git, unlike the 50k-row tables the phase-3 no-JSONL rule
  targeted). Sample is richer than lemma-only on purpose (a few concepts/senses +
  one false-friend pair + one concept relation) so 4.1's SQLite adjacency queries
  get real parity tests, doubling as the phase-9 seed. Consistency call: **Parquet
  stays the single source of truth**; the committed JSONL is a readable seed/input
  (same role the raw OMW/kaikki cache plays for the full corpus), not a competing
  truth - corpus.py's "JSONL never committed" wording gets a sample-seed carve-out.
  Remaining 4.1 sub-decision left for execution: commit the generated sample Parquet
  (lean) vs build it on demand from the JSONL seed.
- 2026-06-16 : executed the CSV->JSONL sample-seed migration. Converted the six
  `data/bootstrap/*.csv` into one committed `lemmas.jsonl` (301 rows, via `load_csv`
  + `deduplicate` - de 'essen'/'Essen' normalize to one id, the intended merge),
  hand-authored `concepts.jsonl` (4: house/water/to-eat cross-lingual + a lemma-less
  `building` hypernym), `senses.jsonl` (18 edges across 6 langs), `false_friends.jsonl`
  (1: es 'embarazada' vs en 'embarrassed'), `concept_relations.jsonl` (1: house
  hypernym building). `git rm`'d the CSVs, force-added the JSONL (data/ is gitignored
  but bootstrap is force-tracked). All seed rows are the lean codec row shape, so the
  store / `import_table` consume them directly.
- 2026-06-16 : executed phase 4.1 (status done). Rewrote `lemma_store.py` to a single
  SQLite engine: `from_models`/`from_data_fol` build a fresh indexed SQLite DB (PK on
  `id`, secondary indexes on the adjacency keys; nested list/dict fields stored as JSON
  text), every query is a `SELECT` reconstructing thin models via the codec. Removed
  resident mode entirely - `LexiconStoreMode`, `SqliteModeNotImplementedError`,
  `_hydrate()`, the list-based constructor, and the bootstrap-CSV->dict load path are
  gone. Back-refs are now opt-in `hydrate_lemma`/`hydrate_concept`/`hydrate_sense`
  (bounded 1-2 hops, fresh instances, no shared identity); `resolve_*` still raises
  until hydrated. Sub-decision resolved: **build SQLite on demand from the committed
  JSONL seed, do not commit Parquet** - `data/` is gitignored and LFS is not
  materialized, so a text-only seed is the clean hermetic source; `sqlite3` is stdlib so
  the seed path needs no `store` extra (preserves "lang-tutor reads lemmas without
  pyarrow"). `from_data_fol` prefers `data/lexicon/` Parquet when present (phase 5),
  else the seed. Rewrote `test_lexicon_store.py` for the SQLite surface + on-demand
  hydration + a `from_data_fol` seed round-trip; webapp lemma/concept APIs stay green.
  Docs updated (`lexicon.md` store/hydration/storage sections, `frozen_api.md` content
  layout). Suite green: 120 passed, ruff clean, pyright 0 errors.
- 2026-06-17 : brainstormed and executed phase 4.2 (status done) - collapsed the
  store's two model-loaders into one. The `from_data_fol` JSONL-seed fallback and
  the pyarrow-missing degrade path are gone; the store reads **Parquet only** and
  raises `CorpusNotFoundError` ("Corpus not found at <path>") when the corpus is
  absent. Rationale (in `04.2_seed_data.md`): pyarrow is mandatory the moment the
  phase-5 Parquet ships, so the stdlib-only seed path bought only a pre-phase-5
  sample convenience at the cost of a permanent second code path + a store/inspect
  divergence. The committed `data/bootstrap/*.jsonl` seed becomes a pure **dev
  input**, turned into the (gitignored) sample Parquet by the new thin
  `notebooks/lexicon_corpus/parquetize_seed.ipynb` (loops `import_table`). Decisions
  folded from the user's answers: `pyarrow` promoted to base `dependencies`,
  `duckdb` stays the inspect-only `store` extra; the eager import-time `_STORE`
  became a **lazy** `get_store()` (+ `set_store`/`reset_store`) so a corpus-less
  checkout stays importable (eager+raise would break every import); store target is
  the existing `data_fol` param, so tests point it at a tmp dir. Rewrote the
  `from_data_fol` test as a Parquet round-trip + a missing-corpus test; added a
  session fixture that parquetizes the seed into a tmp corpus and `set_store`s it for
  the webapp APIs. `explore.ipynb` now builds a store at a chosen folder (commented
  swap line + "parquetize first" note). Docs updated (`lexicon.md`, `frozen_api.md`,
  codec docstring). Suite green: 121 passed, ruff clean, pyright 0 errors. Note:
  `docs/guides/bootstrap_data.md` is stale from before 4.1 (describes CSV +
  in-memory + import-time load) and was left for a separate cleanup.
- 2026-06-17 : executed phase 5 (status done). Built the initial-build pipeline
  under `src/lang_tools/lexicon/ingestion/`: `acquire.py` (raw-cache paths,
  `download_omw` wrapping `wn`, `fetch_kaikki` HTTPS GET, `_build.json` manifest
  read/write), `sources/omw.py` (impure `wn_synset_entries` flattening synsets to
  a pure `SynsetEntry`; pure `group_to_records` grouping by shared ILI into one
  `Concept` + member `Lemma`/`Sense`, with `slugify` + WordNet POS map),
  `sources/kaikki.py` (`load_kaikki_entries` keeping glosses/examples for
  enrichment, joined by `(normalized text, language)`), `transform.py`
  (`TaggedTables` = the five tables + parallel per-row provenance tags; OMW rows
  tagged `omw`, any row gaining CC-BY-SA kaikki content re-tagged `kaikki`),
  `sample.py` (`carve_sample`, slice closed under kept concepts), `pipeline.py`
  (`build_initial`: transform -> codec write w/ tags -> manifest -> carve+write
  sample; senses partitioned per lemma-language). Provenance is the **one seam**
  the deferred merge needs: added `PROVENANCE_COL = "source"` to `codec.py` as an
  on-disk-only extra column - `_dump_table(..., sources=)` writes it (parallel to
  models, partition-aware), `model_from_row` always drops it, so the thin models
  and the SQLite runtime (`_COLUMNS`-driven) stay untouched. `wn` added as a new
  lazy `ingest` optional extra; runtime never imports it. Two thin driver
  notebooks under `notebooks/lexicon_ingest/` (`01_download`, `02_transform`).
  Tests (+28, 149 total): omw grouping/slug/POS/dedup, kaikki parse, transform
  provenance retagging, sample closure, acquire manifest round-trip, pipeline
  build -> store load + provenance-on-disk-dropped-on-load, codec provenance
  round-trip. `uv run pytest && ruff check . && pyright` all green. Docs: new
  "Initial build pipeline (phase 5)" + "Provenance column" sections in
  `docs/library/lexicon.md`; reference pages auto-generate via api-autonav.
  **Not run here** (no network / `wn` not installed in this env): the real
  OMW+kaikki download and the resulting committed sample slice. The pipeline is
  verified end-to-end against in-memory fixtures; a real build is a `01`/`02`
  notebook run on a machine with the `ingest` extra. Deferred per plan:
  re-ingestion smart merge, LLM granularity collapse (seam only).
