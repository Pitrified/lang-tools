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

## Phases (proposed)

| #  | Phase                         | Plan                                                     | Status | One-liner                                                                                                              |
| -- | ----------------------------- | -------------------------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------- |
| 1  | Rename `Word` -> `Lemma`      | [`01_rename_word_to_lemma.md`](01_rename_word_to_lemma.md) | done | Preliminary mechanical refactor `Word`->`Lemma` (and `lang-tutor`) so later phases use literature vocabulary.          |
| 2  | Core data models              | [`02_core_models.md`](02_core_models.md)                 | draft  | Define thin `Lemma`, `Concept`, explicit `Sense` edge, `FalseFriendRelation`, generic relation edge; concept id scheme. |
| 3  | Storage & indexing analysis   | [`03_storage_indexing.md`](03_storage_indexing.md)       | draft  | Assess git-LFS-friendly formats (CSV/JSONL vs SQLite), scale/perf/memory limits, whether a DB can live in LFS.         |
| 4  | Store layer + indexes         | [`04_store_layer.md`](04_store_layer.md)                 | draft  | Extend/replace `lemma_store` with concept/sense/edge registries and look-aside indexes.                                |
| 5  | Initial ingestion pipeline    | [`05_ingestion.md`](05_ingestion.md)                     | draft  | OMW via `wn` -> concepts, then kaikki enrichment, then LLM granularity/mapping; the order and how.                     |
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
