# Bootstrap Sample Seed

`data/bootstrap/` holds a small, committed **JSONL sample seed** for the lexical
graph: a handful of cross-lingual concepts with their lemmas, sense edges, and a
couple of relation edges. It is a **developer input, not a runtime source** - the
store reads Parquet only (see [the lexicon library docs](../library/lexicon.md)).
The seed is the editable, diffable text that the *sample* Parquet corpus is built
from; the full corpus comes from the ingestion phase.

## Files

| File | Table |
|------|-------|
| `lemmas.jsonl` | thin lexical tokens (all languages in one file) |
| `concepts.jsonl` | language-independent concepts / synsets |
| `senses.jsonl` | the lemma <-> concept edges |
| `false_friends.jsonl` | false-friend token pairs |
| `concept_relations.jsonl` | typed concept-to-concept edges |

Each line is one row in the **lean codec shape** - exactly the columns the Parquet
codec persists (`lang_tools.lexicon.codec`), which is the model minus the
store-hydrated back-references. For example a lemma row:

```json
{"id": "5a99...", "text": "Haus", "language": "de", "normalized": "haus", "part_of_speech": "noun", "topics": ["home", "basics"], "examples": [{"sentence": "Ich wohne in diesem Haus.", "translation": "I live in this house."}], "sources": ["csv"]}
```

JSONL (not CSV) because the models carry nested fields - `Concept.definitions` is
a per-language map, `Lemma.examples` is a list of objects - that do not fit a flat
CSV. A ~50-row sample is diffable in normal git, so the seed is committed even
though the large corpus tables are not.

## Turning the seed into a corpus

The store has a single load path: it reads `data/lexicon/` Parquet and raises
`CorpusNotFoundError` when none is present. A fresh checkout therefore has no
runtime corpus until you build one. For the sample, run the parquetize notebook:

```text
notebooks/lexicon_corpus/parquetize_seed.ipynb
```

It loops `lang_tools.lexicon.corpus.import_table` over each seed file, validating
every row through its pydantic model and writing the canonical Parquet under
`data/lexicon/` (gitignored). After that the store and the webapp read the sample.

## How consumers read it

Once the corpus exists, the read surface (used by the webapp and `lang-tutor`) is
the default store, built lazily on first use from the Parquet:

```python
from lang_tools.lexicon.lemma_store import get_all_lemmas, get_lemmas_filtered

lemmas = get_all_lemmas()                  # all lemmas
pt_lemmas = get_lemmas_filtered(language="pt")
food_lemmas = get_lemmas_filtered(topic="food")
```

## Editing the sample

- Edit a `data/bootstrap/*.jsonl` file directly (it is the source), then re-run
  the parquetize notebook to rebuild `data/lexicon/`.
- Or use the validated round-trip in [explore.ipynb](../library/lexicon.md):
  `export_table` -> edit a transient JSONL -> `import_table`, which rewrites the
  Parquet only after every row validates.

Schema changes are not edits: adding or removing a column regenerates the tables
from the ingestion pipeline, never line-patched.
