# Rebuilding the corpus from scratch

The full lexicon corpus (`data/lexicon/*.parquet`) is not committed - only the
small sample seed is (see [Bootstrap sample seed](bootstrap_data.md)). A fresh
clone therefore has no runtime corpus until you build one, and the build is fully
reproducible from public sources. This guide walks a new machine from an empty
clone to a gated, five-language corpus, plus the optional exploration datasets.

Every step is a thin notebook over package code, so the notebooks are the
procedure: run them in order and read the logged numbers.

## What you end up with

| Folder | What it holds | Produced by |
| ------ | ------------- | ----------- |
| `data/_raw/lexicon/wn_data/` | OMW 1.4 wordnets (en, pt, es, fr, it) + CILI, in a `wn` database | `01_download` |
| `data/lexicon/` | the source-of-truth Parquet (`concepts`, `lemmas`, `senses`, `concept_relations`, `sense_relations`, `false_friends`) + `_build.json` manifest | `02_transform` |
| `data/bootstrap/lexicon/` | the carved ~50-concept sample corpus (tests and the webapp read it) | `02_transform` |
| `data/lexicon/_store.sqlite` | the store's derived runtime cache; rebuilds itself on first load | first `LexiconStore` load |
| `data/_raw/lexicon/staging/` | exploration-only datasets (Tatoeba, wordfreq lists, Wikidata lexemes, Kelly CEFR) + `_staging.json` | `00_stage` (optional) |

All of `data/` is gitignored except the committed seed JSONL under
`data/bootstrap/` and the curated inputs under `data/curated/`, which are tracked
through git LFS.

## Prerequisites

### Clone with git LFS

Install and register git LFS **before** cloning, so the committed seed and the
curated gloss overrides arrive as real content rather than pointer stubs:

```bash
git lfs install
git clone https://github.com/Pitrified/lang-tools.git
cd lang-tools
git lfs pull   # only needed if you cloned before installing git LFS
```

The curated overrides matter for the build: `data/curated/gloss_overrides.jsonl`
is re-applied on every rebuild, so a pointer stub here silently drops the
repaired glosses.

### Install the extras

The build needs the `ingest` extra (`wn`, `wordfreq`), the quality gate needs
`store` (DuckDB), and the exploration staging needs `enrich` (`xlrd`, `pandas`,
`matplotlib`). The simplest is all of them:

```bash
uv sync --all-extras
```

### Environment

The params singleton is loaded on import and reads one placeholder secret,
`SAMPLE_API_KEY`. Copy `nokeys.env` to `~/cred/lang-tools/.env` and fill it in
(any value works for `SAMPLE_API_KEY`). No real API key is needed to build the
corpus: every LLM-generated input (gloss repairs, slug qualifiers, form drops, the
gloss backfill) is committed under `data/curated/` and applied by the build.
`OPENAI_API_KEY` only matters to re-run one of those jobs
(`notebooks/lexicon_maintain/`).

### Network, disk, memory

The build downloads from GitHub release assets only:

- `github.com/omwn/omw-data/releases/download/v1.4/omw-{en,pt,es,fr,it}-1.4.tar.xz`
- `github.com/globalwordnet/cili/releases/download/v1.0/cili.tsv.xz`

`wordfreq` ships its data inside the pip package. The optional staging step also
reaches `downloads.tatoeba.org`, `dumps.wikimedia.org`, `query.wikidata.org`, and
`ssharoff.github.io`; allow those if you build behind a restrictive proxy.

Measured on a 4-core, 16 GB machine with no GPU (nothing in the build uses one):

| Step | Wall time | Disk |
| ---- | --------- | ---- |
| download (OMW + CILI) | ~1 min | ~230 MB (`wn_data/`) |
| build (`build_initial`) | ~4 min | ~35 MB (`data/lexicon/`) |
| first store load (builds `_store.sqlite`) | ~30 s | small |
| staging (optional) | ~5 min | ~710 MB, most of it the Wikidata lexeme dump |

Peak memory during the build is just under 2 GB, so leave at least 2 GB free.

## Step 1 - download the sources

Run `notebooks/lexicon_ingest/01_download.ipynb`.

It calls `acquire.download_omw` for the five languages, which downloads one OMW
lexicon per language (not the whole `omw` collection) plus the CILI resource into
`data/_raw/lexicon/wn_data/`. It is idempotent: `wn` skips anything already
installed, so re-running it is cheap. Keep the returned `omw_info` dict in the
kernel; step 2 can record it in the manifest.

## Step 2 - build the corpus

Run `notebooks/lexicon_ingest/02_transform.ipynb`
in the same kernel.

The build cell calls `pipeline.build_initial`, which transforms the OMW cache,
re-applies the curated gloss overrides, adds the phase-6 frequency and CEFR
estimates, writes `data/lexicon/`, and carves the sample into
`data/bootstrap/lexicon/`. Expect it to take about four minutes. The logged summary should
match the row counts in the committed quality report (next step); a healthy run
logs the curated overrides as applied with zero stale.

The notebook does not pass `extra_manifest` to `build_initial`. To pin the source
versions in `_build.json`, as its markdown recommends, change the call to:

```python
summary = build_initial(
    LANGS, data_fol=data_fol, sample_data_fol=seed_fol, extra_manifest=omw_info
)
```

Then:

- The provenance cell should show only `omw`, `cili`, and `llm` sources (no
  `kaikki`).
- **Skip the "Refresh the committed sample seed" cell** unless you mean to move
  the seed. It overwrites the committed `data/bootstrap/*.jsonl`; on an unchanged
  pipeline it should be a no-op, so `git status` showing changes there means the
  build drifted.
- The spot-check cell loads the full store and prints the `house` concept across
  the five languages. The first load also builds `_store.sqlite`.

## Step 3 - run the quality gate

Run `scratch_space/09_concept_model/05.4_data_quality/05.4_data_quality_checks.ipynb`.

It runs `quality.run_quality_checks` over `data/lexicon/` and rewrites the
committed `report.md` beside it. The report leads with eight invariants that must
all read PASS. Because the report is tracked, `git diff` on it is the regression
check: on an unchanged pipeline, only the `Generated:` timestamp should change.
Any other diff is a real change in the corpus. Either explain it or revert the
report.

## Step 4 (optional) - stage the exploration datasets

Run `notebooks/lexicon_enrich/00_stage.ipynb`
only if you will run the `lexicon_enrich` topic notebooks (01-06). The build does
not read any of these.

It stages Tatoeba sentences, per-language wordfreq lists, the CC0 Wikidata lexeme
dump (a large download, skipped when already present), and the Kelly en/it CEFR
lists (validation only, never merged) under `data/_raw/lexicon/staging/`, and
writes `_staging.json` recording each dataset's license. The final cell indexes
English lemmas to Tatoeba sentences, so run it after step 2.

## Running the notebooks headless

The notebooks are written to run interactively in an editor, but the `notebook`
dependency group ships `nbconvert`, so each step also runs from a shell. Write the
executed copy outside the repo, so the committed notebooks stay output-free:

```bash
uv run jupyter nbconvert --to notebook --execute --output-dir /tmp/nb_out \
    notebooks/lexicon_ingest/01_download.ipynb
```

Two caveats when running steps 1 and 2 this way. Each notebook gets its own
kernel, so `omw_info` from step 1 is not available to step 2. And step 2 runs
every cell, including the seed-refresh export, which rewrites the committed seed
JSONL. On an unchanged pipeline that export is byte-identical, so `git status`
stays clean; if it does not, the build drifted. The step-3 gate rewrites
`report.md` the same way.

## Sample-only setup

If you only need the sample (tests, webapp development), skip the build and run
`notebooks/lexicon_corpus/parquetize_seed.ipynb`,
which turns the committed seed JSONL into `data/bootstrap/lexicon/` in seconds.
The test suite does not need the full corpus.

## Troubleshooting

- **`CorpusNotFoundError`** - `data/lexicon/` has no Parquet yet. Run step 2, or
  point the store at `data/bootstrap` for the sample.
- **`KeyError: 'SAMPLE_API_KEY'`** on import - the cred file is missing. See
  [Environment](#environment).
- **`OptionalDependencyMissingError`** - an extra is missing. Run
  `uv sync --all-extras`.
- **`git status` lists the seed files as modified straight after cloning**, and
  checkout refuses to switch branches ("files that should have been pointers") -
  the checked-out branch stores them as plain blobs while `.gitattributes` routes
  `data/**` through LFS. The content is identical. Check with
  `cmp <(git show HEAD:<path>) <path>`, then stash them, or switch with the LFS
  filter bypassed for that one command:
  `git -c filter.lfs.process= -c filter.lfs.clean=cat -c filter.lfs.smudge=cat checkout <branch>`
  followed by `git lfs pull`.
- **Stale or surprising store results after a rebuild** - `_store.sqlite` is keyed
  on the Parquet signature and rebuilds itself. Deleting it is always safe.
