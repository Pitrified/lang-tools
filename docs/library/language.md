# Language module

The `lang_tools.language` package provides everything that depends on the
target language: presets, accent maps, normalisation, and keyboard layouts.

## Languages

A `Language` is a Pydantic model carrying the alphabet metadata that the
exercises and ingestion pipelines need. The shipped presets cover Portuguese,
French, Spanish, Italian, English, and German.

Each `Language` holds:

- Core identity (`code`, `name`, `native_name`).
- Accent metadata (`accented_chars`, `normalization_map`).
- Keyboard layout hints (`keyboard_rows`, `accent_keys`) consumed by
  on-screen input widgets in the wordle and diacritic-typing exercises.

Exercise-specific settings (such as allowed word lengths) are **not** stored
on `Language`. See [`WordleConfig`](exercises.md#wordle) for wordle settings.

```python
from lang_tools.language import LANGUAGE_PRESETS, get_language

pt = get_language("pt")
print(pt.accented_chars)        # {'ã', 'ç', 'ó', ...}
print(pt.keyboard_rows[0])      # ['q', 'w', 'e', ...]
```

`get_language("xx")` raises [`UnknownLanguageError`](../reference/lang_tools/language/language/).

## Normalisation

`normalize(text, language=None)` strips accents and lowercases the input.
With a `Language` it first applies the language-specific
`normalization_map` (currently a no-op for all presets, but available for
custom languages).

```python
from lang_tools.language import normalize

normalize("Café")              # 'cafe'
normalize("Ação", get_language("pt"))  # 'acao'
```

`has_accent(text)` and `extract_accented_chars(text)` are convenience helpers
used by the `Word` model and the diacritic-typing exercise.
