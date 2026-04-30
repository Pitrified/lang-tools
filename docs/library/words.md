# Words

The `lang_tools.words` package owns the canonical vocabulary model and its
ingestion pipelines.

## `Word` model

A `Word` is a Pydantic model that always carries a stable `id`, a normalised
form, frequency tier, translations, glosses, examples, and optional
false-friends. The id is derived from `(text, language)` after normalisation,
so two records that differ only in case or accents collide cleanly.

```python
from lang_tools.words.word import Word

w = Word(text="Café", language="fr", part_of_speech="noun", frequency="medium",
         translations={"en": "coffee"})
w.id            # 16-char sha1 prefix
w.normalized    # 'cafe'
w.has_accent    # True
w.length        # 4
```

See the [`Word`](../reference/lang_tools/words/word/) API reference for the
full schema (`Gloss`, `GlossExample`, `WordExample`, `FalseFriend`).

## Ingestion

`lang_tools.words.ingestion` exposes three loaders, all yielding `Word`
instances tagged with the originating source:

- `load_wiktionary_jsonl(path, language=...)` reads kaikki.org-style JSONL
  Wiktionary dumps. Filters by part-of-speech and skips inflected-form
  pointers by default.
- `load_csv(path)` reads a flat CSV with required columns `text` and
  `language` plus optional translation / topic / example / false-friend
  columns. Raises [`CSVColumnsMissingError`](../reference/lang_tools/words/ingestion/csv_loader/)
  on missing required columns.
- `load_static_list(entries)` ingests an in-memory list of dicts (the
  `worldly-words` flow).

`merge_words(left, right)` and `deduplicate(words)` collapse records that
share an id, preferring the version with richer metadata.
