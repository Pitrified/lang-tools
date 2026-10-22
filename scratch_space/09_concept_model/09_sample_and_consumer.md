---
status: done
---

# Phase 9 - sample data + consumer uplift

Plan of record (2026-10-22). Reconnect `lang-tutor` to the concept model built in phases
2-8. Both repos develop on `feat/lexicon`. Context:
[`00-concepts-brainstorm.md`](00-concepts-brainstorm.md), "Uplift plan (no data
migration)".

The "sample data" half of the original draft is mostly done already: 5.59 carves
`data/bootstrap/` from the build (50 concepts / 587 lemmas over five languages, referentially
closed) and the store loads it. What is left is the consumer.

## Audit (2026-10-22)

`lang-tutor` `feat/lexicon` is one commit past `main` (`dc205e4`, the phase-1 rename to
`Lemma`). Nothing since phase 2 has been carried over.

### Suite status

`uv run pytest` does not collect: `fastapi-tools` is in the `webapp` extra, and the `dev`
group does not pull it in. With `uv sync --all-extras`, **112 tests pass and 11 fail**:

| Failures | Cause | Kind |
| --- | --- | --- |
| 8 (pair matching, diacritic typing, selection) | `Lemma.translations` / `.glosses` / `.frequency` were removed in phase 2 | the real uplift |
| 2 (`test_pages` static assets) | `static/css/app.css` and `static/img/logo.svg` are whitelisted in `.gitignore` but were never committed | pre-existing |
| 1 (`test_env_vars`) | needs `LANG_TUTOR_SAMPLE_ENV_VAR` from `~/cred/lang-tutor/.env` | machine setup, not code |

### Feature by feature

| Feature | Reads today | State | New source in the concept model |
| --- | --- | --- | --- |
| Pair matching | `lemma.translations[target]` | broken | lemmas of the best sense's concept in the target language |
| Diacritic typing | `lemma.glosses`, `translations["en"]` as hints | broken | concept definition in the UI language + the en lemma |
| Wordle | `text`, `normalized`, `length` | works, bad pool | same fields; pool must drop proper nouns, multiword forms and obscure words |
| Sentence reconstruction | `lemma.examples` | silently empty | `Lemma.examples` is empty corpus-wide (0 rows); `Concept.examples` has en (32.9k concepts) and it (1.4k) only |
| Conversational tutor | LLM only | works | unaffected |
| Weighted selection (`select_lemmas`) | `lemma.frequency`, `translations` | broken, and **unused**: the exercise API picks with `random.choice` | best-sense CEFR band + sense frequency |
| Progress (`UserLemmaProgress`) | - | model only: never recorded, never persisted; the progress pages are placeholders | - |
| Lemma pages (`/lemmas`) | `translations`, `frequency` in templates | broken; would also render the whole language (pt 45.9k rows, en 148.7k) | paged search + a detail page with senses |
| Content seam (`ContentSource`) | `get_lemmas_filtered`, `get_lemma_by_id` | works, but every round pulls the whole language pool (in-process or over HTTP) | a bounded, filtered drill query |

Two findings change the earlier notes:

- **The phase-8 "re-key per-user progress" item is moot.** No progress is stored anywhere,
  so no ids need migrating; selection just starts from the new ids.
- **False-friend traps are not possible yet.** `false_friends.parquet` has 0 rows. The
  endpoint and model exist, but the data has to come first, as its own task.

### What the corpus can feed

"Easy" here means the lemma's best sense (highest sense frequency) is A1-B1. "Single" means
one lowercase alphabetic token:

| lang | lemmas | easy | easy single | easy single, 5 letters | easy accented | easy with an own-language example |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| en | 148,695 | 4,706 | 2,543 | 480 | 0 | 3,695 |
| es | 36,492 | 2,031 | 1,776 | 336 | 253 | 0 |
| fr | 51,486 | 2,564 | 2,122 | 356 | 493 | 0 |
| it | 41,765 | 2,185 | 1,927 | 296 | 51 | 453 |
| pt | 45,898 | 2,610 | 2,025 | 411 | 387 | 0 |

Every lemma's best concept has an en and an own-language definition (phase 8 backfill), so
glosses and translations are available everywhere. The only real content gap is example
sentences outside en/it.

## Design

### Decision 1 - the drill view lives in `lang-tools`

The tutor needs a per-lemma answer to "what does this mean, how hard is it, and how do you
say it in X". That is a graph join (lemma -> senses -> best concept -> other-language
lemmas). `lang-tools` owns the graph, the indexes and the HTTP API. If `lang-tutor` did the
join, an exercise round over HTTP would cost one call per lemma. So `lang-tools` gains one
lean, learner-facing read model and one bounded query, and the thin `Lemma` stays as it is.

```python
class LemmaCard(BaseModel):              # lang_tools.lexicon.card
    lemma: Lemma                         # thin token, unchanged
    concept_id: str                      # best sense's concept
    cefr_level: str | None               # of the best sense
    sense_frequency: float | None
    gloss: str | None                    # concept definition in gloss_language
    translations: dict[str, list[str]]   # lang -> lemma texts of the same concept, by frequency
    examples: list[str]                  # concept examples in the lemma's language
```

"Best sense" means the highest `sense_frequency`, with ties going to the easier band. This is
the lemma-level ranking that phase 6 deferred to here. It is computed when the query runs,
not stored on `Lemma` (phase 6 Decision 1 stands).

`CardQuery`:

- `language`
- `gloss_language` (default `en`)
- `translation_languages`
- `max_cefr` / `min_cefr`
- `topic`, `part_of_speech`
- `length`, `accented_only`, `single_word`, `require_translation`, `require_example`
- `exclude_ids`, `limit` (capped, default 50), `seed` (deterministic random sample)

The store method is `LexiconStore.lemma_cards(query)` plus `lemma_card(lemma_id, ...)`. A
`best_sense` table is materialized in `_store.sqlite` when the store is built, so the query
stays an indexed scan rather than a window function per call.

### Decision 2 - HTTP surface

- `GET /api/v1/cards?…` and `GET /api/v1/cards/{lemma_id}`.
- `GET /api/v1/lemmas` gains `q` (prefix on `normalized`), `limit` (default 100, max 500)
  and `offset`.

  The unbounded list is a footgun at 324k lemmas. The tutor is the only consumer and moves in
  lockstep, so changing the default is acceptable. It gets recorded in `frozen_api.md`.

### Decision 3 - `lang-tutor` reads cards, weights locally

- `ContentSource` gains `get_cards(query)` / `get_card(lemma_id)` (in-process and HTTP).
  `get_lemmas_filtered` stays for the lemma pages only, now paged.
- Selection: the server returns a candidate window (for example 4x the round size, seeded,
  filtered by level). `select_lemmas` then applies progress weights locally.
- `compute_weight` swaps `frequency_factor` for a CEFR factor (A1 > ... > C2). Unseen,
  error-heavy and useless handling are unchanged.
- The exercise API uses `select_lemmas` instead of `random.choice`, with in-memory per-session
  progress (no persistence, see Out of scope).
- The learner's level (`max_cefr`, default B1) and UI language (default `en`) are request
  parameters with defaults; there is no settings page yet.

### Decision 4 - exercise mapping

| Exercise | Card query | Uses |
| --- | --- | --- |
| Pair matching | `single_word`, `require_translation=[target]` | `translations[target][0]` as the pair; reject a round where two source cards share a translation |
| Diacritic typing | `accented_only`, `single_word` | `gloss` + `translations["en"]` as hints |
| Wordle | `length=N`, `single_word`, `max_cefr` | `lemma.text` / `normalized`; guesses are still validated against the full same-length list |
| Sentence reconstruction | `require_example` | `examples[0]`; en/it only until sentences exist for pt/es/fr (open question Q1) |
| Conversational tutor | optional: pass 5-10 target-level lemma texts into the prompt as vocabulary | otherwise unchanged |

## Steps

Each step is a commit in its repo, pushed to `feat/lexicon`. No paid LLM calls anywhere
(the tutor chain keeps its fake model by default).

**`lang-tools`**

1. **`LemmaCard` + store query.** Add the model and `CardQuery`. Materialize `best_sense` in
   the SQLite build, add `lemma_cards` / `lemma_card` and the indexes, and test against the
   seed (filters, best-sense tie-break, translation ordering, `limit` cap, seeded
   determinism). Measure latency on the full corpus. Target: under 50 ms for a 200-card
   window.
2. **HTTP.** Add the `cards` router and paging/`q` on `lemmas`, with tests. Update
   `frozen_api.md` and `lexicon.md` and run the gate (row counts unchanged).

**`lang-tutor`**

3. **Tooling baseline.**
   - Make the `dev` sync include the `webapp` extra so `uv run pytest` collects.
   - Commit the missing `app.css` / `logo.svg`.
   - `test_env_vars` stays an environment requirement and gets documented.

   After this step only the 8 removed-field tests fail.
4. **Content seam.** Add `get_cards` / `get_card` to `ContentSource`, `InProcessContentSource`
   and `HttpContentSource`, with tests (HTTP over a mock transport, in-process over the seed).
5. **Selection on cards.** Add the CEFR factor and window-then-weight, and port the selection
   tests.
6. **Exercises.** Port pair matching, diacritic typing, wordle and sentence reconstruction to
   cards, with tests.
7. **Webapp.**
   - The exercise API uses `select_lemmas` with session progress and records each result.
   - The lemma list is paged with search.
   - The lemma detail page shows every sense (gloss, CEFR, frequency, translations,
     synonyms from the concept's same-language lemmas).
   - Port the templates.
8. **End to end + docs.** Run the `lang-tools` service on the full corpus and `lang-tutor` in
   HTTP mode, then play one round of every exercise in pt and en (TestClient script, plus
   browser screenshots). Update both repos' docs, and close this phase in `tracking.md`.

## Result (2026-10-22)

Done. Steps 1-8 ran as planned. The end-to-end run turned up more than the audit
did, and every finding was fixed in place.

**Decisions taken on the open questions:**

- **Q1 (sentences):** the user asked for about ten sentences "to prove it works",
  hand-written rather than generated by a paid model. There are now 10 rows (4 pt,
  3 es, 3 fr) in `data/curated/example_sentences.jsonl`, applied at build like the
  other curated inputs.
- **Q2 (progress):** session-only. `SessionProgressService` in `lang-tutor` keeps
  it in memory per process.
- **Q3 (false friends):** untouched, still empty.

**`lang-tools`:**

- `LemmaCard` / `CardQuery` with `lemma_cards`, `lemma_card` and
  `lemma_sense_cards` (one card per sense).
- A derived `lemma_drill` table, so a 200-card window over the full corpus takes
  20-50 ms. A first draft scanned the fat `lemmas` rows and took 450-600 ms.
- Served at `GET /api/v1/cards`, `/cards/{id}` and `/cards/{id}/senses`.
  `/api/v1/lemmas` is paged (100 per page, max 500), takes a folded prefix `q`,
  and returns the total in `X-Total-Count`.

**Best sense:** the plan said "highest sense frequency, ties to the easier band",
which was wrong outside English. The SemCor split is English-only, so every sense
of a pt lemma ties on frequency, and the tie fell to the alphabetical concept id
(*casa* -> apartment, *falar* -> deal). The tie-break is now `Concept.commonness`
(*casa* -> house, *falar* -> say, *feliz* -> happy).

**Found by the end-to-end run and fixed:**

- `lang-tutor` had never shipped its exercise scripts, `wordle.css`, `app.css`
  or the logo. They sat in gitignored directories that a negated file pattern
  cannot re-include. They were restored from this repo's history.
- `pair_matching.js` still used the pre-rename API keys.
- Wordle's Enter re-clicked the focused New Game button, so guesses never showed.
- Diacritic typing wrote its hint and result to element ids the page does not
  have.
- Sentence reconstruction could never report `finished`.
- The lemma router pointed at templates that were never moved.
- fr "p" (the letter) reached pair matching, hence `CardQuery.min_length`.
- Concept examples are shared by every lemma of the concept (pt *habitação* got
  the *casa* sentence), hence `CardQuery.example_mentions_lemma`.
- OMW-pt lists *teatro* in the dwelling concept, which made dwelling its best
  sense. A hand-written drop row, like avô's, fixed it: senses 491,362 -> 491,361,
  gate PASS.

**Verified:**

- Both suites are green: `lang-tools` 356 + 1 skipped, `lang-tutor` 140.
- With `lang-tools` serving the full corpus and `lang-tutor` in HTTP mode, every
  exercise played in pt, en and fr. Round starts took 12-120 ms. Browser
  screenshots of each page showed no console errors.
- en diacritic typing answers 400 by design, since English has no accented
  lemmas.

**Known limits:**

- WordNet has no function words, so a few frequent forms map to odd senses
  (fr *sans* -> lilac, en *a* -> angstrom).
- OMW-pt membership noise remains beyond the two patched rows (avô, teatro).
- The `lang-tutor` commits could not be pushed from this session (403: the Claude
  GitHub App is not installed on `Pitrified/lang-tutor`).

## Open questions

- **Q1 - sentences for pt/es/fr.** There are no example sentences outside en/it. The options:
  - (a) hide sentence reconstruction for those languages;
  - (b) generate a sentence per round with the existing conversation chain (paid per round,
    off by default);
  - (c) a measured, approved batch job that writes a curated sentence set into `lang-tools`
    (stored content, which `frozen_api.md` calls out of scope for now).

  The proposal is (a) now and (c) as a follow-up.
- **Q2 - progress persistence.** Progress is in memory per session in this plan. A durable
  per-user store (a JSON file or SQLite in `lang-tutor`) would be its own step.
- **Q3 - false friends.** The table is empty. Filling it is a separate data task in
  `lang-tools`, and trap drills wait for it.

## Out of scope

- New exercise types, a settings page, durable progress (Q2) and false-friend data (Q3).
- Licensing and packaging (phase 10). Pinning `lang-tools` to a tag instead of the
  editable path.

## Done when

- `lang-tools`: the card query and endpoints are tested and documented, and the gate passes.
- `lang-tutor`: `uv run pytest && uv run ruff check . && uv run pyright` is green after a
  plain `uv sync`, with no reads of removed `Lemma` fields.
- An end-to-end run plays every exercise on the full corpus over HTTP, with level-appropriate
  words (no proper nouns or multiword targets in wordle or diacritic typing).
