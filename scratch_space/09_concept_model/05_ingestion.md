---
status: done
superseded_in_part_by: 05.5_cleanup.md
---

# Phase 5 - initial ingestion pipeline

> **Partly superseded by [`05.5_cleanup.md`](05.5_cleanup.md) (2026-06-20).** The OMW
> backbone, Parquet-as-source-of-truth, the `source` provenance seam, and the `_build.json`
> manifest below all still stand. The kaikki/Wiktionary enrichment leg has been **removed**
> (drop-kaikki decided 2026-06-18): treat every kaikki acquire/transform/source-module
> reference here as superseded. `Concept.definitions` now come from **OMW glosses plus a
> CILI English fallback** (English-only; non-en stays OMW-only).
>
> **5.5 Step 1 done (2026-06-20):** `sources/kaikki.py` + `wiktionary.py` deleted,
> `_enrich_concepts`/`_enrich_lemmas` gone, `fetch_kaikki` removed from `acquire`, exports
> and the download notebook cleaned, a `test_no_row_is_tagged_kaikki` guard added. The
> `source` enum keeps `kaikki` as a legacy value only.
>
> **5.5 Step 2 done (2026-06-20):** `group_to_records` fills the English gloss from the ILI
> CILI definition when OMW is blank and tags that concept `cili`; `acquire.download_omw`
> now also downloads the `cili` resource. The five-language build shows this fallback fires
> **0 times** (provenance `{omw: 117659}`): an ILI implies a Princeton/English synset, and
> `omw-en` has ~100% gloss coverage, so the English gloss is already present. It is kept as
> a documented dormant safety net for a future English-excluded build.
>
> **5.5 Step 3 done (2026-06-20):** one isolated loader per dataset. CILI moved to its own
> `sources/cili.py` (`load_cili_glosses`), `SynsetEntry` is pure OMW again, and the CILI
> gloss map is threaded as an explicit argument (`load_sources` -> `transform` ->
> `group_to_records`) rather than riding on OMW's records. The loader contract is documented
> in `sources/__init__.py`; Tatoeba/Wikidata stay deferred. So the `Module layout` /
> `sources/` shape below is now `omw.py` (backbone) + `cili.py` (annotator), not `kaikki.py`.
>
> **Still TODO, tracked in 5.5:** promote the permissive OMW fields -
> examples/lexfile/`tag_count`/relations - (Step 4), then rebuild (Step 7).

## Overview

A **one-time initial build** that populates the lexical dataset from external
sources and writes it into the phase-3 Parquet format / phase-4 store. Order:
**OMW (via `wn`) as the concept backbone, kaikki/Wiktionary as enrichment, LLM for
granularity/mapping only** (optional). Context:
[`00-concepts-brainstorm.md`](00-concepts-brainstorm.md) ("Bootstrap source",
"First slice"); builds on the phase-4 `codec.py` seam and the
[`04.1`](04.1_sqlite_mode.md) SQLite-only `LexiconStore` (the runtime engine is
settled before this phase). Extends `src/lang_tools/lexicon/ingestion/`.

## Source-of-truth model (the key decision)

**The Parquet tables under `data/lexicon/` are the source of truth.** Phase 5 does
the *initial* population only. After that:

- Edits (hand or LLM) **update the Parquet directly** through the phase-4 corpus
  tooling (`export_table` -> edit -> `import_table`). There is no separate
  committed-patch / overlay layer - that was rejected: an LLM-driven curation
  stream could grow to 100k lines of patches, and "regenerate examples" style
  edits do not belong in a patch file. The canonical rows just *are* the data.
- A future **re-ingestion of updated OMW/kaikki is a smart merge** against the
  existing (possibly hand-curated) Parquet, not a from-scratch rebuild that
  overwrites curation. **That merge is deferred** - phase 5 does not design or
  implement it (see "Deferred: re-ingestion merge").

This makes phase 5 simple and linear: download -> transform -> write Parquet (+ a
committed sample slice). No base/shipped split, no overlay reapply.

### Provenance as the merge seam (lightweight)

Each row carries a single lightweight `source` tag (`omw|kaikki|llm`, and `manual`
once hand-edited via the corpus round-trip). This is the **one** seam the deferred
merge will need: it lets a future re-ingestion refresh machine-generated rows
while leaving hand-curated rows alone. It stays **off** the thin pydantic models -
an extra Parquet column added to `codec._DROP_ON_LOAD`, same trick as the computed
ids.

**Save enough metadata to rebuild the machine output** (the merge baseline,
decision B). The `data/lexicon/_build.json` manifest pins the exact source versions
(wn wordnet + ILI version, kaikki dump date) and the transform is deterministic, so
"what upstream originally gave us" is **reconstructible** by re-running the pinned
transform against the (regenerable) raw cache - no committed base snapshot needed.
That reconstructible baseline is what a future merge diffs against; whether the
merge ends up 2-way (ours vs new-upstream) or 3-way (old-upstream vs new-upstream
vs ours) is **deferred** - phase 5 only guarantees the baseline can be rebuilt. The
manifest also feeds the phase-10 dataset card.

## Goals

1. Acquire raw OMW + kaikki for `en/pt/es/fr/it` into a local, reproducible cache
   (gitignored - regenerable, not LFS).
2. Transform that cache into `concepts` / `lemmas` / `senses` Parquet (the source
   of truth), each row `source`-tagged, written via `codec._dump_table`.
3. Carve and **commit a small sample slice** for `lang-tutor` + tests.
4. Two thin driver notebooks (download, transform); the existing `explore`
   notebook becomes useful (reads what the transform writes).
5. `LexiconStore.from_data_fol` loads the result; spot-checks confirm cross-lingual
   grouping (shared ILI) and gloss coverage.

## Pipeline (two stages, one truth)

```
sources (OMW via wn, kaikki JSONL)
   │  stage A: acquire   (download → raw cache + _build.json manifest)
   ▼
data/_raw/lexicon/…                  (gitignored; reproducible; not LFS)
   │  stage B: transform (raw → concepts/lemmas/senses, source-tagged)
   ▼
data/lexicon/*.parquet               ← SOURCE OF TRUTH (LexiconStore reads this)
   └─ carve → committed sample slice (for lang-tutor + tests)
```

After stage B, the Parquet is authoritative; further edits go through the phase-4
corpus round-trip, not back through this pipeline.

## Module layout (extends `ingestion/`)

```
src/lang_tools/lexicon/ingestion/
  acquire.py        # download_omw(langs), fetch_kaikki(langs) → raw cache + manifest
  sources/
    omw.py          # wn-backed: synset → (Concept, [Lemma], [Sense]) records
    kaikki.py       # kaikki JSONL → enrichment records (wraps existing wiktionary.py)
  transform.py      # raw cache → source-tagged concept/lemma/sense rows
  sample.py         # carve a small committed slice from the full tables
  pipeline.py       # build_initial(langs, data_fol): acquire? → transform → write → sample
```

Reuses `wiktionary.py` (`load_wiktionary_jsonl`, `WikiRecord`, `WikiSense`) and
`dedup.py`. `wn` is a new lazy-imported dependency (under the `store`/`ingest`
extra) so the base package stays light, same pattern as `pyarrow`/`duckdb`.

### OMW → models mapping

- synset → `Concept` (id `c__{slug}__{hash[:12]}` from ILI key; `definitions` from
  per-language glosses), `source=omw`.
- synset members → thin `Lemma` rows (`lemma_id` = sha1 of `language::normalized`),
  `source=omw`.
- membership → `Sense` edges straight from synset members, `source=omw`.
- ~~kaikki fills sparse `Concept.definitions` / examples, joined by `(lemma,
  language)` onto synsets, `source=kaikki`, license-isolated (phase 10).~~ **Removed in
  [`05.5_cleanup.md`](05.5_cleanup.md):** the sense-blind join was the `house` defect and
  the only CC-BY-SA source. Replaced by a CILI English-gloss fallback (5.5 Step 2);
  examples come from OMW `synset.examples()` / Tatoeba instead (5.5 Steps 3-4).

LLM granularity collapse (over-fine WordNet senses → learner granularity) is an
**optional seam, not a "done" requirement**: deterministic OMW-as-is is the default
output; the LLM pass is wired but off by default and verifiable against OMW.

## Notebooks

Thin callers under a new `notebooks/lexicon_ingest/` (logic stays in the package):

- `01_download.ipynb` → `acquire.*`. Writes raw cache + manifest. Run rarely.
- `02_transform.ipynb` → `pipeline.build_initial`. Writes the source-of-truth
  Parquet + sample slice.

The existing `notebooks/lexicon_corpus/explore.ipynb` is unchanged and starts
returning rows once `02_transform` writes Parquet - it queries via
DuckDB-over-Parquet (`inspect_table`), which does **not** load the corpus resident,
so it inspects full scale fine.

## Deferred: re-ingestion merge

A future refresh of OMW/kaikki must merge new upstream data into the existing,
possibly hand-curated Parquet **without clobbering curation** - using the `source`
tag to decide what is safe to refresh (machine rows) vs preserve (`manual` rows).
This is genuinely the hard part, but it is **rare** (OMW/kaikki move slowly) and
**not needed for the initial build**, so it is deferred. Likely home: its own
later phase or folded into phase 8 (maintenance). Phase 5 only ensures the seam
exists (the `source` column + the manifest).

## Out of scope

- The re-ingestion smart merge (deferred, above).
- Runtime engine work: it is settled *before* this phase in
  [`04.1_sqlite_mode.md`](04.1_sqlite_mode.md) (SQLite-only). Phase 5 just writes
  Parquet the already-built engine reads.
- Frequency / CEFR (phase 6) and semantic relations beyond false friends (phase 7)
  - the schema leaves hooks but populates nothing.
- The ongoing LLM maintenance loop (phase 8); final consumer wiring (phase 9);
  license finalization + dataset card (phase 10, the manifest is its input).

## Done when

- `pipeline.build_initial` produces `concepts`/`lemmas`/`senses` Parquet for the
  five languages, loadable by `LexiconStore.from_data_fol`; spot-checks confirm
  cross-lingual grouping and gloss coverage.
- A committed sample slice exists and the phase-4 store + webapp load it green.
- `source` provenance columns + `_build.json` manifest are written and round-trip
  through the codec (dropped on model load, present in the file).
- `uv run pytest && uv run ruff check . && uv run pyright` passes.
