# wordle settings

## Overview

The wordle settings are embedded in the `Language` base model. This is a
concern-mixing problem: `Language` is a core data model describing a spoken
language (code, name, accent characters, normalization rules), but it also
carries game-UI settings (`word_lengths`, `default_word_length`) that only
make sense in the context of the wordle exercise.

---

## Analysis (as-is)

### What is in `Language` today

`src/lang_tools/language/language.py` defines these fields:

| Field | Type | Concern |
|---|---|---|
| `code`, `name`, `native_name` | `str` | core language identity |
| `accented_chars` | `set[str]` | core - accent/normalization |
| `normalization_map` | `dict[str, str]` | core - accent/normalization |
| `word_lengths` | `list[int]` | **wordle-specific** |
| `default_word_length` | `int` | **wordle-specific** |
| `keyboard_rows` | `list[list[str]]` | borderline - UI layout, used by wordle + diacritic typing |
| `accent_keys` | `list[str]` | borderline - derived from `accented_chars`; on-screen key list |

The docstring even admits this explicitly: *"Each preset bundles the accented
characters set, normalization map, **Wordle word-length config**, and
on-screen keyboard layout."*

### How `word_lengths` / `default_word_length` are actually used

- `WordleExercise.start()` derives word length from `len(normalize(target.text))`.
  It does **not** read `Language.word_lengths` at all.
- The fields exist purely so a frontend/API can know what word-length options
  to present for a given language. They are presentation/filtering metadata,
  not exercise logic.
- `keyboard_rows` and `accent_keys` are not used by any exercise logic either;
  they would be consumed by a UI layer (on-screen keyboard widget).

### Root cause

The fields were copied over from the `worldly-words` React `Language`
interface (`wordLengths`, `defaultLength`), which conflated language identity
with game UI settings because that was the only data model in that repo.
`lang-tools` has a richer model space and can do better.

---

## Other potential leaks into Language (not in scope now)

Two more fields on `Language` are borderline exercise concerns:

| Field | Current home | Exercise(s) that use it | Notes |
|---|---|---|---|
| `keyboard_rows` | `Language` | wordle, diacritic typing | QWERTY layout for on-screen keyboard widget |
| `accent_keys` | `Language` | wordle, diacritic typing | `sorted(accented_chars)` - derived, redundant |

Neither is strictly a language property; both are UI hints for exercise
widgets. They are kept in `Language` for now because:

1. Both exercises use them, so they are not exercise-specific (unlike
   `word_lengths`).
2. They are genuinely per-language (different languages have different
   accented key sets and keyboard layouts).
3. The added model/lookup complexity is not yet justified.

If more exercises accumulate UI configuration, or if the keyboard layout
needs to vary by exercise type, these should move to a dedicated
`KeyboardLayoutConfig` alongside the exercise config files.

`accent_keys` is also a candidate for removal as a field altogether - it is
fully derivable from `accented_chars` via `sorted()`. If kept, a
`@computed_field` would express this more honestly than a stored field.

---

## Plan - decouple wordle settings from Language

### Step 1 - create `WordleConfig` in the exercises layer

`word_lengths` and `default_word_length` are exercise-level settings.
Create `src/lang_tools/exercises/wordle_config.py` alongside `wordle.py`.

Following the config/params pattern: the `Config` model defines the shape
and carries default values as Python literals - the **single canonical
place** those values exist. No Params class is needed here because there
are no env vars, no secrets, and no environment-specific overrides. Callers
simply instantiate the model directly.

```python
# src/lang_tools/exercises/wordle_config.py
"""Wordle exercise configuration."""

from pydantic import Field
from lang_tools.data_models.basemodel_kwargs import BaseModelKwargs


class WordleConfig(BaseModelKwargs):
    """Configuration for a Wordle exercise session.

    Attributes:
        word_lengths:
            Allowed word lengths for the word-length selector.
            Defaults to ``[4, 5, 6, 7]``.
        default_word_length:
            Pre-selected word length when no preference is stored.
            Defaults to ``5``.
    """

    word_lengths: list[int] = Field(default_factory=lambda: [4, 5, 6, 7])
    default_word_length: int = 5
```

Callers instantiate with or without overrides:

```python
from lang_tools.exercises.wordle_config import WordleConfig

config = WordleConfig()                                            # defaults
config = WordleConfig(word_lengths=[5, 6], default_word_length=5) # override
```

### Step 2 - strip wordle fields from `Language`

Remove `word_lengths` and `default_word_length` from `Language` in
`src/lang_tools/language/language.py`. The factory functions (`_pt`,
`_fr`, `_es`, `_it`, `_en`) all relied on field defaults rather than
explicit per-language values, so no change is needed inside them beyond
the model no longer accepting those fields.

Update the `Language` class docstring to remove the Wordle mention.
Update the module docstring - it currently says *"Wordle word-length config"*
is bundled here; remove that claim.

### Step 3 - `keyboard_rows` / `accent_keys`

Keep both fields in `Language`. They are language-level UI hints (on-screen
keyboard layout) shared by wordle and diacritic-typing exercises alike.
Update the `Language` docstring to replace the implicit Wordle framing with
"keyboard layout hints for on-screen input widgets."

### Step 4 - re-export from `exercises/__init__.py`

Add `WordleConfig` to `src/lang_tools/exercises/__init__.py`:

```python
from lang_tools.exercises.wordle_config import WordleConfig
```

Also add it to the `__all__` list.

### Step 5 - update callers

Search for any code reading `language.word_lengths` or
`language.default_word_length` (webapp routes, services, serialisers) and
replace with an instantiated `WordleConfig` at the call site.

### Step 6 - tests

Add `tests/exercises/test_wordle_config.py`:

- Default instantiation yields `word_lengths=[4, 5, 6, 7]` and
  `default_word_length=5`.
- Custom values round-trip correctly through `to_kw()`.

Existing `tests/exercises/test_wordle.py` is unaffected.

### Step 7 - docs

- Update the `Language` narrative page under `docs/library/` to reflect
  the removed fields.
- The `WordleConfig` API reference page is auto-generated from its
  docstring by mkdocstrings.

### Files touched

| File | Change |
|---|---|
| `src/lang_tools/language/language.py` | remove `word_lengths`, `default_word_length`; update docstrings |
| `src/lang_tools/exercises/wordle_config.py` | **new** - `WordleConfig(BaseModelKwargs)` with canonical default values |
| `src/lang_tools/exercises/__init__.py` | re-export `WordleConfig` |
| `tests/exercises/test_wordle_config.py` | **new** unit tests |
| `docs/` | update language + exercise narrative docs |
