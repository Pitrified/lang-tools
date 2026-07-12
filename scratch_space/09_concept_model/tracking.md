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
| 5  | Initial ingestion pipeline    | [`05_ingestion.md`](05_ingestion.md)                     | done* | One-time initial build: OMW via `wn` -> concepts, kaikki enrichment, optional LLM granularity. Parquet is the source of truth; re-ingestion merge deferred. *(\*kaikki enrichment leg superseded by 5.5)* |
| 5.1 | Ingestion fixes (first real run) | [`05.1_ingestion_fixes.md`](05.1_ingestion_fixes.md)  | done   | Fix four defects from the first real OMW/kaikki run: str `ili`, collection-not-per-lexicon download, ambiguous `it` lexicon, kaikki OOM. One `lang->lexicon` map + lazy filtered kaikki stream. |
| 5.2 | Real-run perf follow-ups      | [`05.2_perf_followups.md`](05.2_perf_followups.md)       | draft  | Non-blocking observations from the successful en/pt run: considerable slug collisions (-> phase 8 dedup), >5 min store load (cache / avoid `get_all_*`), borderline memory (per-language build restructure). |
| 5.3 | Load + memory profiling (gate) | [`05.3_load_profiling.md`](05.3_load_profiling.md)      | done | Profiled (>5 min was swap thrash, not CPU; root cause = pydantic double-materialization) and **fixed**: stream lean Parquet rows into a persisted signature-keyed `_store.sqlite`; seed corpus split to `data/bootstrap/lexicon/`. Cold load 16 s / 593 MB (was 1362 MB), warm cache hit ~1 ms. |
| 5.4 | Preliminary data quality checks | [`05.4_data_quality.md`](05.4_data_quality.md)         | draft  | Read-only quality pass over the first build: count/emptiness/cross-lingual-balance/trust checks as bounded DuckDB queries; diagnose the `house` "definition = lemma" defect (sparse OMW glosses + sense-blind kaikki join); full OMW/kaikki metadata catalog (kept/dropped/promote); other datasets + licensing. Routes findings to phases 6/7/8/10. md-only. |
| 5.5 | Cleanup: re-cut around OMW backbone | [`05.5_cleanup.md`](05.5_cleanup.md)            | in progress | Execute 5.4's drop-kaikki decision: hard-delete the kaikki enrichment path, anchor on the concept/gloss/sense triple (OMW + CILI English fallback), one isolated loader per dataset, promote permissive OMW fields (examples/lexfile/`tag_count`/relations) for phases 6/7, LLM cleanup pass, regression-gated rebuild with no CC-BY-SA. Reopens phase 5's enrichment leg. **Steps 1-4 and 6-7 done** (kaikki removed; CILI English fallback; one isolated loader per dataset; Step-4 field promotion; rebuild + gate + license snapshot via 05.56); only Step 5 (LLM cleanup) remains, now sized at a 20-row `def==lemma` residue. |
| 5.54 | Data enrichment (explore first) | [`05.54_data_enrich/05.54_data_enrich.md`](05.54_data_enrich/05.54_data_enrich.md) | exploration done | Sub-plan expanding 5.5 Step 4: stage the candidate datasets (OMW unused fields, CILI, Tatoeba, Wikidata, frequency list, CEFR), then a data-exploration pass over five topics (examples, categories/POS, SemCor + cross-language frequency propagation, relations, complexity) so each enrichment decision is grounded in numbers. Tests the concept-level-vs-language-level propagation assumption rather than assuming it. Findings rewrite Step 4 and feed phases 6/7. |
| 5.55 | LLM cleanup (slug legibility + gloss repair) | [`05.55_llm_cleanup/05.55_llm_cleanup.md`](05.55_llm_cleanup/05.55_llm_cleanup.md) | in progress | Sub-plan executing 5.5 Step 5, sized from the 05.56 gate: deterministic lexfile slug tier (~halves 47,015 colliding concepts; ids rebuilt, never patched; LLM tier-2 qualifiers deferred to phase 8 with the committed-table + Batch-API decisions made) + re-scope the `def==lemma` check to gloss-equals-sole-member and LLM-repair the genuinely-thin remainder; orphan/POS items measured clean and closed. First run of the phase-8 loop shape. **Deterministic slice done** (collisions 47,015 -> 23,476, generic slugs 0, wiki-anchors dropped, def==lemma baseline 7,220 -> 1, gate green); **maintenance loop built and tested** (worklist / proposals JSONL / provenance-preserving apply + gloss-repair chain + driver notebook); remaining: the real one-row propose/review/apply run, blocked on an LLM API key in the cred file. |
| 5.56 | Rebuild + regression gate    | [`05.56_rebuild_gate/05.56_rebuild_gate.md`](05.56_rebuild_gate/05.56_rebuild_gate.md) | done | Executed 5.5 Steps 7+6: 5-language rebuild from the re-cut pipeline (117,659 concepts / 321,126 lemmas / 491,876 senses + 97,666 hypernym edges, ~140 s / 1.5 GB); checks + renderer extracted to `lexicon/quality.py` (notebook = thin caller, report auto-generated); all four invariants pass (`def==lemma` 7,220 -> 20); per-lexicon license snapshot found **omw-pt CC BY-SA / omw-fr CeCILL-C** (routed to phase 10). |
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
- 2026-06-17 : executed phase 5.1 (status done) - the four defects the first real
  OMW/kaikki run surfaced. (A) `wn` 1.1.0's `Synset.ili` is a bare string, not an
  object: added `_ili_id(synset)` (tolerates str / `.id`-object / falsy -> `None`)
  and `wn_synset_entries` uses it. (B/C, shared root) the language was never
  resolved to a concrete lexicon: added `OMW_LEXICONS` (iso -> lexicon id, `it` ->
  MultiWordNet `omw-it`, not `omw-iwn`), `OMW_VERSION`, `_omw_lexicon(lang,
  version)` + `UnknownOmwLanguageError` in `sources/omw.py`. `download_omw` now
  downloads **per lexicon** (the `omw` collection specifier pulled all ~30
  wordnets) and records only the requested specs in the manifest; `wn_synset_entries`
  reads via `wn.Wordnet(lexicon=spec)` (not `lang=`, which merged both Italian
  wordnets non-deterministically). (D, kaikki OOM) kaikki now stays a lazy
  single-pass stream: `load_sources` returns `itertools.chain.from_iterable` of the
  per-language dump generators (was `.extend` into one list), and `transform`
  computes the bounded OMW lemma-key set and keeps only matching entries while
  streaming, so peak memory is `|needed|` not the dump size. `download_omw`'s
  `omw_version` default changed `"omw:1.4"` -> `"1.4"` (bare version; the spec is now
  built from the map). New regression tests: `_ili_id` over str/obj/empty,
  `_omw_lexicon` mapping + `UnknownOmwLanguageError`, and a counting one-shot kaikki
  generator asserting filtered + consumed-exactly-once. Docs: `sources.omw`/`kaikki`/
  `transform` bullets in `lexicon.md` note lexicon-driven selection and the streamed
  bounded enrichment. Pre-existing `wn.config` `reportPrivateImportUsage` (surfaced
  now that `wn` is installed locally) suppressed on the two touched lines. Suite
  green: 153 passed, ruff clean, pyright 0 errors. Still not run here: the real
  download + committed sample slice (needs network + `ingest` extra).
- 2026-06-17 : first **successful** real run of the pipeline (post-5.1) by hand for
  `en` + `pt` - `01_download` + `02_transform` completed and the `explore` notebook
  connected to the resulting store. All 5.1 blockers confirmed fixed on real data.
  Three non-blocking observations recorded as phase 5.2 (status draft,
  `05.2_perf_followups.md`): (1) considerable concept-slug collisions - legibility
  only, ids stay unique via the hash; routed to phase 8's slug-dedup pass.
  (2) the `explore` store load took >5 min on the full en/pt corpus - suspected eager
  `get_all_concepts`-style full-table reconstruction; follow-up is to profile, cache
  the built SQLite, and/or use bounded queries (store-layer, ties to Bug D's "next
  memory ceiling" note). (3) memory borderline on this modest box - the full
  five-language build will likely need the deferred per-language-write restructure.
  None block shipping; the committed sample slice + full build wait on understanding
  (2)/(3) enough to not wedge a small machine.
- 2026-06-17 : planned phase 5.3 (`05.3_load_profiling.md`, status planned) as the
  actionable gate for 5.2's Observations 2 and 3 - profile the >5 min full en/pt
  store load (phase 3 predicts seconds, so the gap is an anomaly to locate, not a
  generic "optimize models"), measure peak build + load memory separately, and
  record two decisions: the load-path/query-shape fix (incl. whether to cache the
  built SQLite and treat bulk `get_all_*` as a smell vs the DuckDB inspect path),
  and a go/no-go on the per-language-build restructure (5.1 Bug D's "next memory
  ceiling") before the full five-language build. Measurement + a decision, not a
  rewrite. Gates the committed sample slice and phases 6/7. 05.2 stays the
  observation record; 5.3 is the measure-and-fix.
- 2026-06-17 : profiled phase 5.3 (status in progress) against the real en/pt corpus
  (192k lemmas / 118k concepts / 272k senses) via
  `05.3_profiling/profile_load.py` (crash-survivable log to `profile_run.log` -
  needed because the first attempt OOM-killed). **Key result: the >5 min load is
  swap thrash, not CPU.** With RAM free the real `from_data_fol` runs in ~21.5 s; the
  killer is **peak RSS 1362 MB** (en/pt alone) from `_load_corpus_models` building
  all ~580k pydantic models for all tables and holding them while `_populate`
  re-dumps each via `row_from_model`. pydantic validate is cheap (~5-9 us/row,
  ~3.7 s total) - it is the *retention* of every model that drives memory, and
  memory is what makes the box thrash/OOM. The 05.2 guess (eager `get_all_concepts`)
  was wrong - the load dominates, not the bulk read. Measured the fix: stream lean
  Parquet rows straight into SQLite, skipping the pydantic round-trip -> 11.9 s /
  702 MB (~1.8x faster, ~½ memory). Provisional five-language go: streaming likely
  makes it feasible (~1.5 GB) without the per-language-write restructure (5.1 Bug D);
  re-measure at five langs before deciding. Side findings: 15,740 colliding slug
  groups out of 118k concepts (Obs 1 quantified; also `_warn_on_slug_collisions`
  spams ~15.7k log lines per load - should summarize), and stale tiny seed
  partitions (de/es/fr/it ~50 rows, senses/_all 18) mixed into the committed corpus
  from an earlier parquetize-seed run. Two open decisions before applying the fix:
  keep opt-in on-load validation? persist the built SQLite (`db_path`) keyed on the
  manifest vs rebuild `:memory:` each process? Findings written into
  `05.3_load_profiling.md`.
- 2026-06-17 : executed phase 5.3 fix (status done) on the user's decisions (skip
  on-load validation by default, persist SQLite, split the seed corpus). Shipped:
  `codec.load_raw_table` (model-free lean Parquet read - drops provenance,
  normalizes map columns) + a shared `_table_paths`/`_read_table_rows` helper;
  `LexiconStore.from_data_fol(validate=False, use_cache=True)` now **streams** each
  table's raw rows straight into SQLite one at a time (no ~580k-model
  materialization) and **persists** the DB to `<corpus>/_store.sqlite`, reused while
  a content signature (sha256 over each parquet's relpath/size/mtime + `CACHE_VERSION`)
  is unchanged - a warm load is a bare `sqlite3.connect`. `validate=True` keeps the
  old model-validating path; `db_path=":memory:"` / `use_cache=False` skip the cache.
  `_warn_on_slug_collisions` now logs **one** summary line (was ~15.7k). Seed/corpus
  split: `parquetize_seed.ipynb` builds `data/bootstrap/lexicon/` (its own corpus,
  co-located with the JSONL seed, gitignored) instead of the real `data/lexicon/`;
  `explore.ipynb` defaults to that seed corpus with a commented swap to the real
  build, and steers bulk reads to `inspect_table` (DuckDB) over `get_all_*`.
  `get_store()` default stays the real corpus (no seed fallback, per 4.2); conftest
  unaffected (already builds a tmp corpus + `set_store`). Re-measured on real en/pt
  (`05.3_profiling/profile_after_fix.py`): cold load 16.1 s / **593 MB** (was 21.5 s /
  1362 MB), warm cache hit **0.001 s**, validate path 23.3 s / 1485 MB. >5 min/OOM
  resolved. Provisional five-language go: cold ~1.2-1.5 GB projected, feasible +
  paid once via the cache, so the per-language-write restructure (5.1 Bug D) stays
  deferred (re-measure at five langs). Tests +3 (raw==validate, cache persist+reuse,
  cache busts on change); ruff gained a `scratch_space/*` ignore block. Suite green:
  156 passed, ruff clean, pyright 0 errors.
- 2026-06-18 : drafted phase 5.4 (`05.4_data_quality.md`, status draft) - a read-only
  quality pass over the first build (md-only, no code/data edits). Specified the
  preliminary checks as bounded DuckDB (`inspect_table`) queries, not a store load
  (honours 5.3: `get_all_*` reconstruction is the cost): volumes + edge reconciliation,
  emptiness/degenerate cardinality (empty/single-member/single-language concepts,
  lemmas-without-sense, dangling edges), cross-lingual balance + ILI-backed vs
  monolingual share + per-language kaikki match rate, and trust/dedup signals (OMW-vs-
  kaikki POS agreement, slug collisions, `definition == lemma`, near-dup lemmas).
  Diagnosed the notebook's `house` case: not a bug but two stacked quality defects -
  sparse non-English OMW glosses + a sense-blind `(text, language)` kaikki join that
  attaches a lemma's most-common gloss to whatever synset it is a member of, so the
  family-sense concept gets the building gloss or a bare `house` translation. Wrote
  three companions under `05.4_data_quality/`: `models_explained.md` (Concept/Lemma/
  Sense field-by-field with source+meaning, POS-trust answer, the `house` diagnosis),
  `metadata_catalog.md` (every OMW/`wn` + kaikki field marked kept/dropped/promote?,
  with a promote shortlist: synset examples, the relation graph, `tag_count` sense
  freqs, lexfile, kaikki tags/topics, per-lexicon licenses), and `other_datasets.md`
  (CILI, BabelNet, Wikidata Lexemes/CC0, ConceptNet, PanLex, wordfreq, SUBTLEX, Kelly,
  EVP/Oxford, Tatoeba - metadata/access/license, with a phase-10 licensing-posture
  table). Findings route to 6 (freq/CEFR), 7 (relations), 8 (gloss/slug/POS cleanup),
  10 (license tallies); only reconciliation failures are must-fix-now phase-5 bugs.
  Two corrections to the brainstorm flagged: "OMW is Apache-2.0" is too broad (per-
  lexicon, verify) and wordfreq is frozen/mixed-license data (pin + verify).
- 2026-06-18 : ran the 5.4 checks on the **real full build** (en/pt/es/fr/it: 117,659
  concepts / 321,126 lemmas / 491,876 senses). Build is referentially clean (zero
  dangling edges, zero lemmas-without-sense, POS fully mapped). Headline findings: 70.4%
  multi-language concepts; gloss coverage en 100% -> it 87.5% -> fr 76.7% -> pt 71.5% ->
  es 70.1%; 7,220 `definition == lemma` rows (6,568 concepts); ~27% slug collisions (top:
  common verbs); kaikki touches ~53% of concept glosses (CC-BY-SA surface). New defect
  found: kaikki glosses often land under the wrong language and are English text / junk
  (`PSEUDOGAP!`) / form-of notes - sense-blind join. Made the notebook self-generate
  `report.md` (a `cap`/`write_report` harness; re-running regenerates it) and validated
  it end-to-end on the corpus. Recorded an **emerging direction**, then
  **resolved with the user (2026-06-18)** and cross-linked into the brainstorm + phase 6:
  (1) **drop kaikki** - lemma-only entries contribute nothing to what we need (a good
  English gloss from OMW/ILI + good concept grouping); per-language glosses are not a
  priority, so dropping it loses nothing we care about and removes the junk *and* the only
  viral license; examples (if wanted) from Tatoeba (CC-BY), no LLM gloss backfill needed
  for the core. (2) **No hard frequency cap** - frequency is a priority/ranking signal,
  not a corpus boundary; keep low-freq lemmas that are well-connected or pedagogically
  important (e.g. irregular verbs); long-tail pruning is an optional cleanup pass only, so
  phase 6 stays annotation + prioritization. (3) Overlapping licenses: CC0 vs permissive/
  attribution vs viral share-alike; one SA source caps the whole corpus at CC-BY-SA and
  can't be relicensed down; license rides on text not facts. Accepting all-CC-BY-SA is
  *valid* but strictly worse (forecloses downstream reuse) and unnecessary once kaikki is
  dropped, leaving a clean permissive + CC0 + CC-BY stack.
- 2026-06-20 : drafted phase 5.5 (`05.5_cleanup.md`, status draft) - the *act* step that
  executes 5.4's drop-kaikki decision (5.4 was measure-only). Seven steps: (1) hard-delete
  the kaikki enrichment path from ingestion (loader, `_enrich_concepts`, manifest entries,
  deps; guard test that no built row is `source=kaikki`); (2) guarantee the English gloss +
  add a permissive CILI fallback (`source=cili`), keep only real non-en OMW glosses; (3) one
  isolated loader per dataset (OMW backbone, CILI fallback, Tatoeba/Wikidata deferred),
  cross-source fills sense-aware or they don't ship; (4) promote permissive OMW fields now -
  `synset.examples()` (home = `Sense` edge, attached at each source's granularity), lexfile,
  `sense.id` + `tag_count`/SemCor weights, hypernym/hyponym + antonym edges - feeding phases
  6/7, with frequency/connectivity also ranking enrichment priority; (5) LLM cleanup pass
  (slug dedup, `definition==lemma` repair, orphan review, OMW-internal POS review, optional
  license-clean gloss backfill), propose-for-review; (6) maintenance loop re-running the 05.4
  checks as a regression gate; (7) rebuild en/pt/es/fr/it and snapshot a no-CC-BY-SA posture.
  Propagated into 05_ingestion (banner + `superseded_in_part_by`; the kaikki leg flagged
  superseded with a still-TODO list; row marked `done*`), 06/07/08/09/10 (cleanup-input
  notes; phase 10's CC-BY-SA open question marked resolved), and the 05.4 companions. Added
  the 5.5 row to the phase table. Also tightened the global CLAUDE.md style rule (drop hype
  adjectives/adverbs; plain headers, no parentheticals).
- 2026-06-20 : implemented 5.5 **Step 1** (remove kaikki from the ingestion code; hard
  delete). Deleted `sources/kaikki.py` + `wiktionary.py` (`KaikkiEntry`, `WikiRecord`,
  `WikiSense`, `load_wiktionary_jsonl`) and their tests; dropped `_enrich_concepts` /
  `_enrich_lemmas` from `transform.py` so `transform(omw_entries)` is OMW-only and tags
  every row `omw`; removed `fetch_kaikki` / `kaikki_path` / `UnknownKaikkiLanguageError` /
  the kaikki URL+lang map from `acquire.py`; dropped `kaikki_entries` from `load_sources` /
  `build_initial` in `pipeline.py`; cleaned both ingestion `__init__.py` exports; removed
  the `fetch_kaikki` import+cells from `01_download.ipynb`. `SOURCE_KAIKKI` kept as a
  documented legacy provenance value (no writer sets it; old Parquet still round-trips
  through the codec). Rewrote the transform/pipeline/acquire tests to OMW-only and added a
  standing guard `test_no_row_is_tagged_kaikki`. No kaikki-specific dependency existed
  (stdlib `json`/`urllib`), so none was removed; `wn` stays for OMW. Verified: 146 passed,
  ruff clean on changed paths, pyright 0 errors. Definitions now come from OMW glosses only
  - the CILI English fallback is Step 2 (pending), so non-en gloss coverage is expected to
  drop until then. Updated 05_ingestion.md (Step-1-done banner) and 05.5 (Step 1 status).
- 2026-06-20 : implemented 5.5 **Step 2** (guarantee the English gloss + CILI fallback).
  `sources/omw.py`: added the `SOURCE_OMW`/`SOURCE_CILI` provenance constants (owned here,
  re-exported by `transform`), a `SynsetEntry.ili_definition` field, and the English-gloss
  fallback in `group_to_records` - when OMW left a concept's English gloss blank it fills
  from the ILI's CILI definition and tags that concept `cili` (non-en glosses stay OMW-only,
  blank when OMW has none). `group_to_records` now returns a 4th value, the per-concept
  source tags; `transform` threads them into `TaggedTables.concept_sources`. `wn_synset_entries`
  loads the ILI glosses once (`wn.ili.get_all()` -> `ILI.definition()`, keyed by id) and
  stamps `ili_definition`; `acquire.download_omw` now also `wn.download("cili")` (recorded in
  the manifest as `ili_resource`). API note: in `wn` 1.1.0 `synset.ili` is a bare id string,
  not an object, so the gloss is read via the loaded CILI resource, not `synset.ili.definition()`;
  with no resource the fallback just does not fire. Tests: updated `test_omw` for the 4-tuple,
  added fallback-fires / not-when-english-present / cili-threads-through-transform cases.
  Verified: 149 passed, ruff clean, pyright 0 errors. Updated 05_ingestion.md (Step-2 banner)
  and 05.5 (Step 2 status). Steps 3-7 remain.
- 2026-06-20 : ran the kaikki-free five-language build via the notebooks (01_download +
  02_transform) to validate Steps 1-2 end-to-end. Result: 117,659 concepts / 321,126 lemmas
  / 491,876 senses (matches the pre-cleanup shape); CILI loaded (117,659 ILI glosses); concept
  provenance is `{omw: 117659}` with **no kaikki and no cili**. So the Step-1 guard holds on
  real data and the **Step-2 CILI fallback fires 0 times**: structurally, an ILI exists only
  because a Princeton/English synset does and `omw-en` (Princeton WN 3.0) has ~100% gloss
  coverage, so every ILI-backed concept already has an English OMW gloss; non-English concepts
  that lack one are ILI-orphans the CILI lookup cannot reach. Decision (with the user): **keep
  the CILI fallback as a documented dormant safety net** (cheap ~1s ILI load) for a future
  English-excluded build, rather than removing it. Annotated the fallback in `sources/omw.py`
  and updated 05.5 / 05_ingestion / metadata_catalog with the finding. Added loguru progress
  logs to both notebooks plus a provenance-check cell (asserts no kaikki).
- 2026-06-20 : implemented 5.5 **Step 3** (one isolated loader per dataset). Pulled CILI out
  of the OMW adapter into its own `sources/cili.py` (`load_cili_glosses` -> `{ili_id: gloss}`,
  streaming `find_ilis`), so `SynsetEntry` is pure OMW again - dropped the `ili_definition`
  field it carried in Step 2 (OMW's record holding another source's data). The CILI gloss map
  is now an explicit input threaded through: `load_sources` returns `(omw_entries,
  cili_glosses)`; `build_initial`/`transform` take a `cili_glosses` arg; `group_to_records`
  applies the fallback keyed by ILI id. Wrote the loader contract into `sources/__init__.py`
  (create-rows vs annotate-by-declared-key; sense-aware-or-it-doesn't-ship; per-row source +
  license) with the adapter registry (omw backbone, cili annotator, Tatoeba/Wikidata
  deferred, kaikki removed). Tests now exercise the fallback via the gloss-map param (added
  ili-orphan and no-map cases). Verified: 151 passed, ruff clean, pyright 0 errors. Updated
  05.5 (Step 3 status) and 05_ingestion (Step-3 banner). Steps 4-7 remain.
- 2026-06-21 : drafted phase 5.54 (`05.54_data_enrich/05.54_data_enrich.md`, status draft) -
  a sub-plan that expands 5.5 Step 4, which was under-specified (it named fields to promote
  and asserted their granularity without data). Reframed it as explore-first: a Stage-0 that
  stages every candidate dataset (OMW unused fields, CILI, Tatoeba, Wikidata slice, a
  per-language frequency list, a CEFR/graded list for validation - each with manifest +
  license), then a data-exploration pass over the five topics from the brief (examples,
  categories/POS, SemCor + cross-language frequency propagation, relations, complexity). Each
  topic is written as what-we-want / candidate-datasets / open-questions / exploration /
  decision-it-unlocks. The cross-cutting axis is concept-level (propagates across languages)
  vs language-level (per-lemma); the propagation hypothesis (common concept = common word
  everywhere; obscure concept = hard word everywhere) is to be tested against real data, not
  assumed. Findings rewrite Step 4 from "promote these fields" to "promote these fields, at
  this granularity, with this propagation rule" and feed phases 6/7. Added the 5.54 row to the
  phase table and a banner on 5.5 Step 4 linking the sub-plan. No code yet.
- 2026-06-21 : implemented phase 5.54 **Stage 0** (dataset staging). New
  `src/lang_tools/lexicon/ingestion/staging/` subpackage, one adapter per candidate
  dataset following the `sources` discipline (network / optional-dep work isolated,
  pure cores unit-tested): `base.py` (staging paths, the `StagedDataset` record, the
  `_staging.json` manifest read/write, a zstd Parquet writer, a known-license
  registry), `tatoeba.py` (`download_tatoeba_sentences` HTTPS fetch + `parse_tatoeba_tsv`
  + the sense-blind, word-boundary, accent-insensitive, capped `build_lemma_sentence_index`),
  `frequency.py` (`stage_frequency_list` via lazy `wordfreq` -> `(word, rank, zipf)`,
  `EnrichDependencyMissingError`), `wikidata.py` (`probe_wikidata_lexemes` CC0
  count+sample with pure SPARQL builders), `cefr.py` (`stage_cefr_list` parsing a
  user-provided graded list for validation only - no baked download), and `__init__.py`
  (the staging contract + registry, exports, `omw_cili_staged_records`). Added `wordfreq`
  as a new lazy `enrich` optional extra in `pyproject.toml`. Lean
  `notebooks/lexicon_enrich/00_stage.ipynb` wires the calls and writes the manifest; logic
  stays in the package. Tests (+21, under `tests/lexicon/ingestion/staging/`): base
  paths/manifest/parquet round-trip, Tatoeba parse + index (token-not-substring, multiword
  contiguity, accent-insensitive, cap), Wikidata query builders + result flatteners + lang
  map, CEFR parse + CSV->parquet stage, frequency dependency guard (happy path gated on the
  extra). Verified: 172 passed / 1 skipped, ruff clean (the only repo ruff errors are
  pre-existing in the 05.4 scratch notebook), pyright 0 errors. Docs: a "Stage 0 dataset
  staging" subsection in `lexicon.md`. Updated 05.54 (Stage-0 code-landed note). Network /
  `wordfreq` calls not run here; the staging notebook run is the next step.
- 2026-06-21 : phase 5.54 Stage-0 follow-ups from the first staging run. (1) **Tatoeba
  index perf** - the first `build_lemma_sentence_index` was O(sentences * forms) (millions
  x hundreds of thousands) and never finished after 6 min; rewrote it to a token-driven
  O(sentences * tokens) scan (single forms via a token->form dict, multiword via bounded
  n-grams up to the longest indexed form), with per-sentence dedupe. (2) **Wikidata** - the
  public SPARQL endpoint 429s (~1 req/min, a global count is the culprit), so it is not
  viable for a real pull; added the **CC0 lexeme dump** path (`WIKIDATA_LEXEME_DUMP_URL`,
  ~590 MB `latest-lexemes.json.gz`): `stream_lexeme_dump` + pure `parse_lexeme_dump_records`
  + `stage_wikidata_lexeme_dump` (per-language tables, exact counts, streamed). Kept
  `probe_wikidata_lexemes` as a gentle fallback - backs off on 429 honouring `Retry-After`,
  count off by default. (3) **CEFR** - confirmed no clean permissive multilingual list:
  Kelly (en/it) is the real download but `.xls` + CC-BY-NC-SA, pt/es/fr have none (estimate
  in phase 6), Oxford/EVP guidance-only. Encoded `KNOWN_CEFR_SOURCES` + `CefrSource` and a
  delimited-URL `download_cefr_list`; acceptable since the list is validation-only and never
  shipped. URLs verified via web (Wikimedia dumps index; the Leeds Kelly mirror). Tests +9
  (Tatoeba dedupe, Wikidata dump parser / `_first_lemma` / unknown-language). Verified: 176
  passed / 1 skipped, ruff clean, pyright 0 errors. Updated the 00_stage notebook (dump path +
  CEFR registry cells), `lexicon.md`, and 05.54 (Stage-0 source assessment). Network /
  `wordfreq` / dump downloads still not run here.
- 2026-06-21 : made Stage-0 fully automatic and ran the small downloads. Added
  `download_lexeme_dump` (streams the ~590 MB CC0 dump in 8 MiB chunks, creates the
  dir - the cause of the manual `curl` failure - skips if present) and
  `download_cefr_source` (downloads + parses a registered CEFR source by name).
  Added `xlrd` to the `enrich` extra and a `read_xls_cefr_rows` reader so the Kelly
  `.xls` lists parse directly (no manual conversion). Verified the real Kelly files
  and found their per-language sheets differ: **en** is `ID/Word/Part of Speech/CEFR/
  Points` (levels wrapped in curly quotes `“A1”`), **it** is `Lemma/Pos/Points` with
  the CEFR band in `Points`; fixed the registry columns and added curly-quote level
  cleaning. Ran the staging for real into `data/_raw/lexicon/staging/`: frequency
  (wordfreq, 50k rows x en/pt/es/fr/it), CEFR (Kelly en 7549 rows clean A1-C2; it
  6865 rows, ~1516 with a blank band - a real Kelly-it quirk), and wrote
  `_staging.json`. The Wikidata 590 MB dump and Tatoeba per-language sentence
  downloads are left to a notebook run (too large to pull here). The 00_stage notebook
  now downloads + stages everything automatically (prereq `uv sync --extra enrich
  --extra ingest --extra store`). Tests +3 (curly-quote levels, unknown /
  undownloadable CEFR source); the frequency happy-path test now runs (wordfreq
  installed). Verified: 178 passed / 1 skipped, ruff clean, pyright 0 errors.
- 2026-06-21 : built + ran the five phase-5.54 **topic exploration notebooks**
  (`notebooks/lexicon_enrich/01_examples` .. `05_complexity`), each a thin caller
  over the staged cache + OMW wordnets ending in a findings cell. Added `pandas` +
  `matplotlib` to the `enrich` extra (notebooks only; the package never imports
  them). Key findings, all reproduced by the cells: every OMW-sourced field
  (examples, definitions, lexfile, relations) sits on the English synset but every
  synset is 100% ILI-linked, so all are concept-level and propagate for free.
  Topic 1: OMW examples en 27% / it 4% / pt-es-fr 0%; Tatoeba richer but
  sense-blind + CC-BY -> ship OMW only, defer Tatoeba. Topic 2: lexfile en-only
  (45 lexfiles) but ILI-resolved; synset POS clean (`n v a s r`). Topic 3: SemCor
  covers 17% of en senses (skewed); concept commonness correlates 0.47 with en
  frequency and predicts es 0.34 / it 0.49 -> the propagation hypothesis holds.
  Topic 4: synset graph dense (hypernym/hyponym 89,089 each, 7% isolated); antonym
  / derivation are sense-level. Topic 5: lemma frequency strongest vs Kelly CEFR
  (-0.66); the concept-level difficulty call holds in 87% of en->it cases.
  Findings folded into 05.54 (Findings section + done-when ticks) and `lexicon.md`.
  Verified: pytest 178 passed / 1 skipped, ruff clean (src/tests/notebooks),
  pyright 0 errors; all five notebooks execute end to end with no errors. Findings
  folded into 05.54 (Findings section + done-when ticks) and `lexicon.md`.
- 2026-06-21 : rewrote **05.5 Step 4** from "promote these fields" to "promote at
  this granularity, with this propagation rule", citing the topic findings. The
  settling fact: every OMW field sits on the English synset but every synset is
  100% ILI-linked, so all are concept-level and propagate. Examples: OMW only
  (concept-level, fan out to senses), Tatoeba deferred (lemma-level, sense-blind,
  CC-BY). lexfile: concept-level field on `Concept` (en-only source, ILI-resolved).
  SemCor: carry `sense.id` through; commonness is concept-level and propagates
  (weighting + cross-language prior are phase 6). Relations: hypernym/hyponym (+
  holonym/meronym/similar) from the synset traversal, antonym from the sense
  traversal, all ILI-keyed; expose connectivity to phase 6.
- 2026-06-21 : implemented the **05.5 Step 4 first slice** (the three concept-level
  fields, end to end). `Concept` gained `lexfile` (str) + `examples`
  (`dict[str, list[str]]`, per-language, sorted/de-duped); `SynsetEntry` gained
  `lexfile` / `examples` / `hypernyms`; `group_to_records` now also builds
  `Concept.lexfile` (English synset preferred), `Concept.examples`, and the OMW
  `hypernym` `ConceptRelation` edges via a two-pass `(language, synset_id) ->
  concept_id` resolution (child=`concept_id_a`, parent=`concept_id_b`; hyponymy is
  the reverse read, not stored; unresolved targets dropped + logged). Threaded
  through `transform`, codec (concepts schema +`lexfile` string +`examples`
  `map<string,list<string>>`; `_MAP_COLUMNS`/`_JSON_COLUMNS` updated) and the SQLite
  store; `lemma_store.CACHE_VERSION` -> 2. Decisions baked from the review: examples
  not duplicated (concept grain on `Concept`, `Lemma.examples` reserved); antonym
  deferred (sense-level, needs a new edge table, kept in mind); the cross-language
  sense-split prior marked **approximate** (no non-en per-sense signal; always
  `frequency_is_estimated`); the Kelly -0.66 marked partly circular; Wikidata parked;
  `derivation` excluded. Tests +5 (lexfile preference, per-language example dedupe,
  directional hypernym edge, dedupe+dangling drop, plus codec/store round-trip of the
  new fields). Verified: 182 passed / 1 skipped, ruff clean, pyright 0 errors. Docs:
  `lexicon.md` Concept + relation sections; 05.5 Step 4 implemented banner + caveats;
  06 prior/CEFR caveats. Deferred: phase-6 weighting, phase-7 antonym +
  holonym/meronym/similar + connectivity.
- 2026-06-21 : folded the 5.54 findings into **phase 6** (a 5.54 banner: two
  frequency signals with the concept one propagating, the English sense split as
  cross-language prior, concept-level complexity validated against Kelly en/it;
  added a concept-commonness bullet and the validation-only Kelly note) and
  **phase 7** (a 5.54 banner on the measured graph: dense ILI-keyed synset edges,
  sense-level antonym/derivation, 7% isolated; added connectivity + holonym/meronym
  as cheap add-ons). All five 05.54 done-when items are now ticked; phase status
  set to "exploration done". Markdown only - no code touched.
- 2026-06-22 : planned the next 5.5 step. Wrote sub-plan **05.56 (rebuild +
  regression gate)** executing Steps 7+6 together: the five-language corpus was
  last built 2026-06-18, before kaikki removal and the Step-4 field promotion, so
  the on-disk corpus and `05.4_data_quality/report.md` still describe a
  kaikki-tagged world. The sub-plan rebuilds from the re-cut pipeline (verifying
  `lexfile` / `examples` / hypernym edges are populated), extracts the 05.4 DuckDB
  checks + report renderer into a tested package module run only from the notebook
  (per review: no slice-based pytest gate - too much complexity deciding how to
  slice; the report is auto-generated wholesale on each run, never copy-pasted),
  confirms four invariants (kaikki share 0, edge-reconciliation 0,
  `definition == lemma` sharply down vs the 7,220 baseline), and snapshots
  per-lexicon OMW licenses (the blanket "Apache-2.0" is wrong). Sequenced
  **before Step 5 (LLM cleanup)** so the
  LLM budget is sized from the clean corpus's real residue, ranked by the
  frequency / connectivity signals Step 4 fed in. Linked from 05.5 Step 6 and the
  tracking table. Markdown only - no code touched.
- 2026-07-11 : executed phase 5.56 (status done) - the rebuild + gate + license snapshot,
  closing 5.5 Steps 7 and 6. Housekeeping first: deleted the five obsolete raw kaikki
  dumps (~5.6 GB reclaimed). Stage A: `download_omw` reused the cached wn data (CILI
  included) and the full en/pt/es/fr/it rebuild ran in ~140 s at 1536 MB peak - the
  per-language restructure (5.1 Bug D / 5.2 Obs 3) stays unnecessary. Result: 117,659
  concepts / 321,126 lemmas / 491,876 senses (same OMW backbone shape) plus the new
  Step-4 payload: 97,666 hypernym `ConceptRelation` edges, `lexfile` on 100% of concepts
  (45 distinct), `examples` on 33,396 concepts (en 32,921 + it 1,435); provenance `{omw}`
  only, CILI fallback fired 0 times (dormant as documented); sample slice re-carved.
  Stage B: extracted the 05.4 checks + report renderer into
  `src/lang_tools/lexicon/quality.py` - a named-check registry returning typed
  `CheckResult`s, four `InvariantResult`s, and a markdown renderer; `report.md` is
  generated wholesale, never authored; the 05.4 notebook shrank to a 3-cell thin caller;
  8 unit tests on a tiny synthetic corpus (S608 waived per-file, same rationale as
  corpus.py). All four invariants pass on the rebuilt corpus: kaikki rows 0, dangling
  sense/relation endpoints 0, lemmas-without-sense 0, `definition == lemma` **7,220 ->
  20 rows** - so the Step-5 LLM gloss-repair budget is tiny; slug collisions (~27%)
  remain the phase-8 bulk. Non-en gloss coverage dropped to real OMW coverage as
  accepted: en 100%, it 6.1%, pt/es/fr 0% (those wordnets ship no definitions).
  Stage C: per-lexicon license snapshot via `wn` metadata (confirmed against the OMW 1.4
  index): en = WordNet license, es/it = CC BY 3.0, but **omw-pt = CC BY-SA and omw-fr =
  CeCILL-C** - the "no CC-BY-SA anywhere" prediction fails at the lexicon level; upstream
  OpenWordnet-PT is now CC-BY 4.0, so a pt re-source is the clean fix; decision routed to
  phase 10 (banner added there). Docs: quality-checks section in `lexicon.md`. Suite
  green: 190 passed / 1 skipped, ruff clean, pyright 0 errors. Next: 5.5 Step 5 (LLM
  cleanup) sized from the 20-row residue, then phases 6/7.
- 2026-07-11 : drafted phase 5.55 (`05.55_llm_cleanup/05.55_llm_cleanup.md`, status draft) -
  the sub-plan for 5.5 Step 5, sized from the fresh 05.56 gate instead of the sketch. Two
  of the five sketch items measured **closed** (0 orphan / 0 no-gloss concepts; POS fully
  mapped with no null bucket) and gloss backfill stays deferred, so the phase reduces to:
  (A) slug legibility via tiered construction in the pipeline - measured that
  slug+lexfile deterministically resolves only ~half the collisions (47,015 colliding
  concepts / 15,740 groups -> 23,476 / 9,782 remain as true same-lexfile polysemy, e.g.
  two `aaron` persons), so tier 2 is an LLM gloss-derived qualifier per group,
  propose-for-review, baked in as a committed build input; ids are **rebuilt, never
  patched** (a slug changes `c__{slug}__{hash}` everywhere; lang-tutor unaffected, lemma
  ids stable); (B) classify the 20 `def==lemma` rows (mostly benign gloss==other-member
  coincidences like Baton Rouge / "capital of Louisiana", a few genuinely thin) and
  LLM-repair via export/import with `source=llm`; (C) record keep-all policy for
  multiword/digit/long lemmas after a spot-check. Five open questions (tier-2 now vs
  phase 8, commit the qualifier table, re-scope the def==lemma check for benign
  coincidences, suspicious-lemma policy, model tier) left as Q1-Q5 ANS placeholders in
  the sub-plan. Banner added on 05.5 Step 5; row added to the phase table. Markdown only -
  no code touched.
- 2026-07-11 : resolved 5.55's open questions with the user and promoted the sub-plan to
  **planned**. Q1: slug tier 2 (LLM qualifiers) **deferred to phase 8** - this phase ships
  the deterministic tiers 0-1 only (halves the 47,015 colliding concepts at zero LLM
  cost); Q2: when phase 8 runs tier 2, the reviewed qualifier table is a **committed
  build input** (small JSONL in normal git, keyed by ILI grouping key); Q3: the
  `definition == lemma` check is **re-scoped** to count only gloss-equals-sole-member
  (benign gloss-equals-other-member coincidences like Baton Rouge / "capital of
  Louisiana" are valid OMW glosses and stay untouched), baseline re-measured; Q5:
  estimated the LLM job instead of picking a tier blind - tier-2 qualifiers batched
  ~25 groups/request = ~1.5M in / ~0.3M out tokens, via the Batch API (-50%) ~$1.50
  (Haiku 4.5) / ~$3 (Sonnet 5 intro) / ~$7.50 (Opus 4.8), so cost does not constrain
  the model choice; this phase's gloss repair (~20 rows) is <$0.10 on any tier. Q4
  (suspicious-lemma keep-all policy) stays open with the keep-all proposal standing.
  Consequence: 5.55's only LLM chain is the gloss-repair one; the tier-2 spec + cost
  estimate handed to phase 8 (banner added in 08_maintenance.md). Markdown only.
- 2026-07-11 : answered 5.55's Q4 by spot-checking the suspicious-lemma categories on
  the rebuilt corpus. Multiword (115,044: "water pill", "Sir John Ross"), digit-bearing
  (1,063: "atomic number 100", "39th", "December 31"), and very-long English (673:
  taxonomy / organization names) are all legitimate - **keep the categories**. The long
  tail exposed real, localized junk: **32 fr lemmas are URL-encoded Wikipedia anchors**
  ("...#Le th.C3.A9.C3.A2tre...", from WOLF's wiki derivation) - to be dropped
  deterministically in 5.55's pipeline pass (with their senses; gate reconciliation
  guards against orphaning) - and ~150 non-en sentence-like forms (gloss pasted as the
  member form, e.g. pt "alimentar um bebê com o leite...") flagged to phase 8 review
  rather than auto-dropped (fuzzy boundary with legitimate long names). Folded into
  the sub-plan (Q4 ANS + work item C). All five 5.55 questions are now resolved;
  the plan stays **planned** and is ready to execute. Markdown only.
- 2026-07-11 : executed 5.55's deterministic slice (status -> in progress). Tier-1
  slugs (`_tiered_slugs` in `sources/omw.py`: keep the tier-0 slug when unique, append
  the slugified lexfile on collision or for the generic `concept` fallback) + the Q4
  wiki-anchor drop (`is_malformed_form`, `#`/`.c3.` case-insensitive; 44 member forms
  -> -29 lemmas / -31 senses, 0 left, no concept orphaned) + the Q3 re-scope of
  `definition == lemma` in `lexicon/quality.py` (shared `_def_eq_sole_member_hits` CTE;
  gloss must equal the *sole* member form; invariant now "at most the baseline").
  Rebuild (112 s / 1.5 GB) hit the predictions exactly: colliding concepts 47,015 ->
  23,476 (groups 15,740 -> 9,782), generic slugs 0; re-scoped def==lemma = **1**
  (19 of the 20 old-scope rows were benign coincidences; baseline 7,220 -> 1; the one
  thin row is `c__mind-noun-cognition__93923c10626c`, it gloss "attenzione"). All four
  gate invariants PASS; report.md regenerated; closed items (POS clean, orphans clean,
  suspicious-lemma policy) recorded. 198 tests / ruff / pyright green; docs updated
  (lexicon.md: slug tiers, re-scoped invariant, stale kaikki pipeline prose removed).
  Remaining in 5.55: the gloss-repair chain + propose -> review -> apply loop for the
  single `attenzione` row.
- 2026-07-12 : built 5.55's maintenance loop (the phase-8 shape): `lexicon/maintenance.py`
  (`thin_gloss_worklist` reuses the gate's sole-member CTE; `GlossProposal` JSONL
  write/read; `apply_gloss_proposals` edits concepts at the raw-row level because the
  generic export/import round-trip drops the `source` column - untouched rows keep
  their tag, edited rows re-tag `llm`), `llm/gloss_repair.py` + `gloss_repair/v1.jinja`
  (proposal-only, grounded in member forms / en gloss / lexfile / hypernym gloss), and
  the thin driver `notebooks/lexicon_maintain/gloss_repair.ipynb`. Loop tested end to
  end on a seeded corpus; worklist verified on the real corpus (1 entry, full context).
  The real one-row run is **blocked on credentials**: `~/cred/lang-tools/.env` has no
  LLM API key, so propose -> review -> apply waits for one. 206 tests / ruff / pyright
  green; docs updated (lexicon.md maintenance-loop section, llm.md chain row).
  Handoff: the user runs the `gloss_repair.ipynb` notebook themselves; 5.55 closes
  after their review + apply + gate re-run.
