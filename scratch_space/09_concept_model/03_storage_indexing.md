---
status: done
---

# Phase 3 - storage & indexing analysis

## Overview

A research/decision phase (mostly analysis, little code) that picks how the
lexical dataset sits on disk and how it is queried at runtime, and validates that
choice stays git-LFS friendly at the dataset's real scale. It gates the store
layer (phase 4) and ingestion outputs (phase 5), and may feed small changes back
into the models (phase 2). Context:
[`00-concepts-brainstorm.md`](00-concepts-brainstorm.md), "Storage format,
git-LFS friendliness, and scaling".

The central reframing this phase makes (from the web survey below): **storage
format and query engine are two separable axes, not one choice.** The brainstorm
framed it as "line-oriented files vs a SQLite blob", but tools like DuckDB query
CSV / JSONL / Parquet files *directly* with full SQL and no import step
([DuckDB docs](https://duckdb.org/docs/current/data/parquet/overview)), so we can
keep LFS-friendly files **and** get indexed/analytical queries on top of them
without committing an opaque database binary. The decision therefore splits into
(a) what bytes we ship and (b) what reads them, and the two are chosen
semi-independently.

This stays an **analysis + decision memo** phase. No loaders or indexes are
built here (phase 4) and no data is produced here (phase 5); the output is a
recorded decision backed by measured numbers and a drafted `.gitattributes`
strategy.

## Goals

1. Separate the **distribution/storage format** axis (how bytes sit on disk and
   churn in git/LFS) from the **runtime access** axis (how the app reads them),
   and evaluate each on its own merits rather than as a single coupled choice.
2. Survey the realistic candidates per axis (done below from web research) and
   reduce them to a short list with the trade-offs that actually bite at our
   scale and access pattern.
3. Pin down the **real scale** with measured numbers on a representative sample
   (size per format, import latency, resident memory, point-lookup latency), not
   order-of-magnitude guesses.
4. Decide the git-LFS strategy: what is tracked in normal git vs LFS, and how the
   corpus is partitioned so one edit does not re-push everything.
5. Produce a decision memo (folded back into the brainstorm) that confirms or
   overturns the provisional recommendation below, with the numbers attached.

## The two-axis framing

### Axis A - distribution / storage format (the bytes we ship)

| Option | Diff / review | LFS churn | Size | Notes |
| ------ | ------------- | --------- | ---- | ----- |
| **JSONL / CSV** (line-oriented) | textual `git diff`, reviewable in PRs; can live in **normal git** if small enough | n/a if in normal git; if in LFS, whole-file re-push | largest (row-oriented, repetitive keys) | human-inspectable; appends cleanly; the current bootstrap format |
| **Parquet** (columnar) | none (binary); not line-diffable | binary blob, whole-file re-push on any change | smallest - columnar compression cuts ~70-75% vs row formats ([KDnuggets](https://www.kdnuggets.com/building-your-modern-data-analytics-stack-with-python-parquet-and-duckdb), [Neural Engineer](https://medium.com/neural-engineer/converting-jsonl-to-parquet-a-technical-guide-c1b42025b48c)) | open, standardized, stable format; row-group stats enable projection/filter pushdown |
| **SQLite file** | none (binary) | binary blob, whole-file re-push | compact | great for point lookups (indexed, row-at-a-time); single-file; ubiquitous stdlib support |
| **DuckDB native `.duckdb`** | none (binary) | binary blob, whole-file re-push | compact | **avoid as the shipped artifact**: forward/backward compatibility is best-effort and can break across versions (the official remedy is "export to Parquet, re-import") ([DuckDB storage docs](https://duckdb.org/docs/current/internals/storage)); one benchmark also showed it ~2-3x slower and far more memory than Parquet ([issue #9965](https://github.com/duckdb/duckdb/issues/9965)) |

Key nuance for LFS: **git LFS stores each version as a whole object and does not
delta-compress**, so the "diffability" advantage of JSONL/CSV only pays off when
the files are small enough to stay in **normal git** (real textual diffs + PR
review). Once a file is big enough to need LFS, the line-oriented diff benefit is
gone and Parquet's compactness (smaller objects, fewer bytes re-pushed) wins.
This makes the size measurement (goal 3) the pivot of the whole decision.

### Axis B - runtime access (what reads the bytes)

| Option | Best at | Cost | Fit |
| ------ | ------- | ---- | --- |
| **In-memory dicts** (today's `_LEMMAS_BY_ID`) | trivial point lookups and small filters; zero deps | whole dataset resident in RAM at import | fine while the corpus fits comfortably in memory |
| **SQLite** | indexed **point lookups** (`get_lemma_by_id`), our dominant pattern; SQLite beats DuckDB on point queries ([Better Stack](https://betterstack.com/community/guides/scaling-python/duckdb-vs-sqlite/), [MotherDuck](https://motherduck.com/learn/duckdb-vs-sqlite-databases/)) | needs an indexed `.db`; lazy disk reads | the natural step if memory becomes the limit |
| **DuckDB over files** | analytical scans/aggregations; reads Parquet/CSV/JSONL directly, glob patterns, `read_json_auto` | extra dep; columnar engine optimized for OLAP, not point lookups | useful for ingestion/QA analytics and ad hoc queries over the shipped Parquet, less so for the hot per-lemma path |

The app's hot path is point lookups and small filters (by id, language, topic;
false-friends-by-lemma), which favors in-memory dicts or SQLite over a columnar
analytical engine. DuckDB earns its place mainly as a **build/QA-time tool** that
queries the shipped files directly without an import step.

## Scale reality check

OMW across the five target languages is on the order of **10^5 synsets** and
**10^6 senses**, plus lemmas and edge tables. This is "medium", not big-data:
even as verbose JSONL it is plausibly tens-to-low-hundreds of MB, and as Parquet
materially smaller. The measurement (below) decides three thresholds:

- Does the full corpus fit comfortably in RAM at import (keep in-memory dicts) or
  not (move to SQLite/lazy access)?
- Are the per-table files small enough for **normal git** (keep JSONL/CSV for
  diffability) or must they go to **LFS** (then prefer Parquet)?
- Where does the point-lookup latency of an on-disk option cross from
  "imperceptible" to "worth the extra dependency"?

Source-side note: the `wn` library used for OMW ingestion (phase 5) already keeps
its data in a **SQLite** db at `~/.wn_data/wn.db`
([wn on PyPI](https://pypi.org/project/wn/)), so SQLite tooling is already in the
dependency graph and is a low-friction option for the runtime store too.

## git-LFS mechanics & partitioning

- **What goes where**: schemas, loaders, and small/curated tables stay in normal
  git; only the large generated corpus is tracked via LFS
  (`git lfs track "data/.../*.parquet"`, quoted so the shell does not expand it
  [git-tower](https://www.git-tower.com/learn/git/faq/handling-large-files-with-lfs)).
- **Partitioning** so one edit does not re-push the whole corpus: per table
  (lemmas / concepts / senses / false-friends / concept-relations) and likely per
  language for the lemma/sense tables, since LFS re-uploads each changed object
  wholesale.
- **Alternatives noted, not adopted**: DVC and similar are aimed at multi-GB ML
  artifacts and add a separate workflow/server
  ([DagsHub](https://dagshub.com/blog/best-data-version-control-tools/)); overkill
  for a medium, mostly-append corpus. LFS is the pragmatic default; revisit only
  if the corpus grows past a few hundred MB per file.

## Sequencing with phase 4

This phase is planned in lockstep with phase 4 but executed first. Phase 4's
**query surface and access-pattern list**
([`04_store_layer.md`](04_store_layer.md), "Query surface & access patterns") is
the benchmark target: the experiments below measure *those* reads (id point
lookups, sense-table adjacency, symmetric false-friend fan-out) rather than
generic queries, so the format/engine choice reflects the real workload.

To avoid throwaway reimplementation, the experiment (de)serialization is written
against phase 4's **codec seam** (`_load_table` / `_dump_table`): the timing and
sizing harness is disposable scratch code, but the winning codec is promoted into
the phase-4 loader rather than rewritten. Phase 4's store implementation
deliberately waits on this phase's decision so it is never built on an
unvalidated format.

## Measurement plan (how the decision gets made)

1. Build a **representative sample** (one or two languages end-to-end via the
   phase-5 ingestion, or a synthetic generator sized to the 10^5/10^6 estimate)
   covering all five tables.
2. Serialize it to each candidate format (JSONL, CSV where applicable, Parquet,
   SQLite) and record **on-disk size** per table and total, compressed and not.
3. Measure **import latency** and **resident memory** for: load-all-into-dicts
   (current), SQLite open + indexed point lookup, and DuckDB-over-Parquet.
4. Measure **point-lookup latency** (`get_lemma_by_id`, false-friends-by-lemma)
   and one representative filter (lemmas by language+topic) for each access
   option.
5. Tabulate against the three thresholds in "Scale reality check" and write the
   memo.

## Provisional recommendation (to confirm with numbers)

Refines the brainstorm's lean ("partitioned JSONL/CSV under LFS, SQLite only if
needed") with the two-axis view:

- **Ship Parquet, partitioned per table (and per language where it helps)** as
  the canonical corpus: smallest LFS objects, open/stable format, and directly
  queryable by DuckDB for build/QA without an import step.
- **Keep a JSONL export path** for human inspection / debugging, and keep any
  small curated tables in **normal git** as JSONL/CSV for real diffs.
- **Runtime access stays the in-memory dicts** of phase 4 initially (the corpus
  is expected to fit in RAM); promote the hot tables to **SQLite point lookups**
  only if the memory or latency measurement says so. **Do not** ship a `.duckdb`
  or `.sqlite` file as the canonical artifact - the former has cross-version
  stability risk, and both are opaque blobs that churn in LFS as badly as Parquet
  while losing Parquet's openness.

This is explicitly provisional: the measured numbers in the memo confirm or
overturn it, especially the "fits in normal git vs needs LFS" pivot.

## Decision memo (measured)

Experiments in
[`03_storage_indexing/03.1_performance_tests.ipynb`](03_storage_indexing/03.1_performance_tests.ipynb)
on a synthetic corpus at the OMW 5-language scale (400k lemmas, 100k concepts,
1M senses, 50k false-friend edges, 200k concept-relation edges), lean persisted
shape (source fields + `id`, dropping cosmetic computed fields).

### Axis A - on-disk size (per table, MB)

| table | rows | jsonl | parquet.zstd | sqlite |
| ----- | ----: | ----: | -----------: | -----: |
| lemmas | 400k | 78.6 | **11.9** | 54.0 |
| concepts | 100k | 14.5 | **1.2** | 16.8 |
| senses | 1M | 226.9 | **22.6** | 135.2 |
| false_friends | 50k | 5.8 | **1.0** | 4.9 |
| concept_relations | 200k | 24.6 | **4.2** | 22.3 |
| **TOTAL** | | **350.3** | **40.9** | 233.1 |

- Parquet+zstd is **~8.6x smaller than JSONL** (40.9 vs 350.3 MB) and beats
  snappy (72.5 MB total).
- **LFS pivot:** as JSONL, `senses` (227 MB) **exceeds GitHub's 100 MB hard push
  limit** and `lemmas` (79 MB) trips the 50 MB warning - the big tables need LFS
  regardless, and LFS does not delta-compress, so JSONL's diff advantage is lost
  exactly where it would matter. As Parquet+zstd every per-table file is < 25 MB;
  per-language partitioning of `senses`/`lemmas` drops each to ~5 MB.
- Small curated tables (`false_friends` 5.8 MB, `concept_relations` 24.6 MB as
  JSONL) are small enough to stay in **normal git** for real diffs / PR review.

### Axis B - runtime access

- Resident memory as in-memory pydantic dicts (current store): lemmas 745 MB
  (400k) + concepts 77 MB + senses ~1,075 MB (1M, extrapolated) = **~1.9 GB**.
  SQLite / DuckDB open lazily at ~0 MB resident.
- Query latency (us/op): point lookup `get_lemma_by_id` - dict **3.0**, SQLite
  (indexed) **30**, DuckDB/Parquet **16,500**; false-friend fan-out - dict 0.6,
  SQLite 34, DuckDB 8,900; lang+topic filter - dict (look-aside index) 0.1,
  SQLite (LIKE scan) 152,800, DuckDB (parquet scan) 150,100.

### Decision (confirms / sharpens the provisional lean)

1. **Ship Parquet (zstd), partitioned per table and per language** for
   `senses`/`lemmas`, under git-LFS. Smallest objects, open/stable, directly
   DuckDB-queryable for build/QA. *(confirmed)*
2. **Ship *all* tables as Parquet under LFS - including the small curated ones -
   for uniformity** *(overturns the provisional "small tables as JSONL in normal
   git")*. Rationale: one distribution path with no special cases (so re-pointing
   the "CDN"/source later touches one mechanism); a 50k-row textual diff is not
   meaningfully reviewable anyway; and a model change (adding a column) rewrites
   every JSONL line, so line-diffability is a false comfort that just risks a
   messy whole-file rewrite. Human inspection/editing is served by the explicit
   workflow below rather than by committing line-oriented files.
3. **Runtime: in-memory pydantic dicts only for the tiny bootstrap/sample data.**
   For the full corpus ~1.9 GB resident is infeasible (e.g. a 512 MB Render
   dyno), so **promote the hot tables to SQLite indexed point lookups** (~30 us,
   ~0 resident). This is now a *measured trigger*, sharpening the provisional
   "dicts initially" into "dicts for sample, SQLite for full corpus".
4. **Do not ship `.duckdb` or a single canonical `.sqlite`** as the artifact;
   DuckDB stays a build/QA reader (16 ms point lookups confirm it is wrong for
   the hot path), and any runtime SQLite is *built from Parquet*, not the shipped
   source of truth.
5. **Every filtered / adjacency access needs an explicit index** (look-aside dict
   or SQLite secondary index): a columnar / LIKE scan is 4-5 orders of magnitude
   slower than an indexed lookup (150 ms vs ~30 us).

### Drafted `.gitattributes` / partitioning

Every table is Parquet under LFS (uniform; no normal-git JSONL artifact):

```gitattributes
# entire generated corpus -> LFS, one rule, no special cases
data/lexicon/**/*.parquet  filter=lfs diff=lfs merge=lfs -text
```

Partition the large tables `senses`/`lemmas` per language as
`data/lexicon/<table>/<lang>.parquet` so one language's re-ingest re-pushes only
~5 MB, not the whole corpus; small tables (`concepts`, `false_friends`,
`concept_relations`) are a single Parquet each.

### Inspect / edit workflow (any table)

Since nothing human-readable is committed, inspection and editing are explicit
operations over the canonical Parquet, both routed through the phase-4 codec seam
(`_load_table` / `_dump_table`):

- **Inspect (read-only):** DuckDB queries the Parquet directly with full SQL and
  no import step - `SELECT * FROM 'data/lexicon/senses/en.parquet' WHERE ...`. A
  thin CLI wraps this for humans/QA, e.g.
  `python -m lang_tools.lexicon.inspect <table> [--lang L] [--where SQL]
  [--limit N] [--format table|jsonl|csv]`, printing rows or dumping a slice.
- **Edit (round-trip, validated):** symmetric `export_table(name, fmt="jsonl")`
  -> hand/LLM edit the JSONL -> `import_table(name, path)` which **validates every
  row through the pydantic model** (catching a renamed/missing column or bad
  value) and rewrites the canonical Parquet. The JSONL is a transient scratch
  file, never committed.
- **Schema changes are not edits:** adding/removing a column is a model change, so
  the table is **regenerated from the ingestion pipeline** (phase 5), consistent
  with the project's "no data migration" decision - never patched line-by-line.

## Out of scope

- Implementing the loaders / registries / indexes (phase 4) and producing the
  real data (phase 5). This phase only measures and decides.
- Any change to the phase-2 models beyond what the format choice forces (e.g. a
  field type that does not round-trip through Parquet), which would be flagged
  back to phase 2.

## Done when

- The two-axis decision is made with **measured numbers** backing it (size,
  import latency, memory, point-lookup latency on a representative sample).
- A `.gitattributes` LFS strategy and partitioning scheme are drafted.
- The decision memo is folded into `00-concepts-brainstorm.md` and recorded in
  the tracking Log, with the provisional lean above confirmed or overturned.

## References

- DuckDB - Reading and Writing Parquet, direct file querying:
  <https://duckdb.org/docs/current/data/parquet/overview>
- DuckDB - Storage Versions and Format (native-format stability caveat):
  <https://duckdb.org/docs/current/internals/storage>
- DuckDB native vs Parquet performance/memory (issue #9965):
  <https://github.com/duckdb/duckdb/issues/9965>
- DuckDB vs SQLite (point lookups vs analytics): Better Stack
  <https://betterstack.com/community/guides/scaling-python/duckdb-vs-sqlite/>,
  MotherDuck <https://motherduck.com/learn/duckdb-vs-sqlite-databases/>
- Parquet vs JSON/JSONL compression and pushdown: KDnuggets
  <https://www.kdnuggets.com/building-your-modern-data-analytics-stack-with-python-parquet-and-duckdb>,
  Neural Engineer
  <https://medium.com/neural-engineer/converting-jsonl-to-parquet-a-technical-guide-c1b42025b48c>
- git LFS handling and `.gitattributes`:
  <https://www.git-tower.com/learn/git/faq/handling-large-files-with-lfs>
- Data-versioning alternatives (DVC etc., noted not adopted): DagsHub
  <https://dagshub.com/blog/best-data-version-control-tools/>
- `wn` library stores OMW in SQLite (`~/.wn_data/wn.db`):
  <https://pypi.org/project/wn/>
