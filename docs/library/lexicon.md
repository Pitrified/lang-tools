# Lexicon

The `lang_tools.lexicon` package owns the canonical lexical model and its
ingestion pipelines.

## `Lemma` model

A `Lemma` is a Pydantic model that always carries a stable `id`, a normalised
form, frequency tier, translations, glosses, examples, and optional
false-friends. The id is derived from `(text, language)` after normalisation,
so two records that differ only in case or accents collide cleanly.

```python
from lang_tools.lexicon.lemma import Lemma

lemma = Lemma(text="Café", language="fr", part_of_speech="noun", frequency="medium",
              translations={"en": "coffee"})
lemma.id            # 16-char sha1 prefix
lemma.normalized    # 'cafe'
lemma.has_accent    # True
lemma.length        # 4
```

See the [`Lemma`](../reference/lang_tools/lexicon/lemma/) API reference for the
full schema (`Gloss`, `GlossExample`, `LemmaExample`, `FalseFriend`).

## Ingestion

`lang_tools.lexicon.ingestion` exposes three loaders, all yielding `Lemma`
instances tagged with the originating source:

- `load_wiktionary_jsonl(path, language=...)` reads kaikki.org-style JSONL
  Wiktionary dumps. Filters by part-of-speech and skips inflected-form
  pointers by default.
- `load_csv(path)` reads a flat CSV with required columns `text` and
  `language` plus optional translation / topic / example / false-friend
  columns. Raises [`CSVColumnsMissingError`](../reference/lang_tools/lexicon/ingestion/csv_loader/)
  on missing required columns.
- `load_static_list(entries)` ingests an in-memory list of dicts (the
  `worldly-words` flow).

`merge_lemmas(left, right)` and `deduplicate(lemmas)` collapse records that
share an id, preferring the version with richer metadata.
