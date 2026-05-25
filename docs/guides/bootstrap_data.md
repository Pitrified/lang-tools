# Bootstrap Word Data

The `data/bootstrap/` directory contains starter vocabulary CSV files for each supported language. These are loaded automatically by the webapp at startup.

## Available Languages

| File | Language | Words |
|------|----------|-------|
| `pt.csv` | Portuguese | ~50 |
| `fr.csv` | French | ~50 |
| `es.csv` | Spanish | ~50 |
| `it.csv` | Italian | ~50 |
| `de.csv` | German | ~50 |
| `en.csv` | English | ~50 |

## CSV Format

Each CSV uses the format expected by `lang_tools.words.ingestion.csv_loader.load_csv()`:

```csv
text,language,part_of_speech,frequency,topics,translation_en,example_sentence,example_translation
casa,pt,noun,high,"home,basics",house,Eu moro nessa casa.,I live in this house.
```

Required columns: `text`, `language`

Optional columns:
- `part_of_speech` - noun, verb, adjective, etc.
- `frequency` - high, medium, or low
- `topics` - comma-separated topic tags
- `translation_<lang>` - one column per target language (e.g. `translation_en`)
- `example_sentence` + `example_translation`
- `false_friend_language`, `false_friend_word`, `false_friend_meaning`, `false_friend_similarity`

## How the Webapp Uses This Data

The webapp loads all bootstrap CSVs automatically via `lang_tools.words.word_store`:

```python
from lang_tools.words.word_store import get_all_words, get_words_filtered

# All loaded words
words = get_all_words()

# Filter by language
pt_words = get_words_filtered(language="pt")

# Filter by topic
food_words = get_words_filtered(topic="food")
```

No database setup is needed. The word store is an in-memory read-only list populated at module import time.

## Adding More Words

1. Edit or add a CSV in `data/bootstrap/` following the format above.
2. Restart the webapp. Words are loaded on startup.

For programmatic ingestion from other sources (Wiktionary, LLM-generated), see the ingestion modules:

```python
from lang_tools.words.ingestion.csv_loader import load_csv
from lang_tools.words.ingestion.wiktionary import load_wiktionary_jsonl

# Load a custom CSV
words = list(load_csv(Path("my_words.csv")))
```

## Using the Ingestion Pipeline in a Script

```python
"""Example: load bootstrap CSVs and print stats."""
from pathlib import Path
from lang_tools.words.ingestion.csv_loader import load_csv

bootstrap_dir = Path("data/bootstrap")
for csv_path in sorted(bootstrap_dir.glob("*.csv")):
    words = list(load_csv(csv_path))
    print(f"{csv_path.name}: {len(words)} words")
    accented = sum(1 for w in words if w.has_accent)
    print(f"  - {accented} with accents")
```
