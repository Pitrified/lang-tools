"""Re-key the curated rows that name a pt lemma by its pre-reform spelling (phase 6).

The build now respells pt lemmas (`respell_pt`), so a row keyed on the old
lemma id would go stale. Every pt text field is respelt and its id field
re-minted; rows are kept in order, so latest-row-wins still reads them the
same way. Dry by default; ``--write`` rewrites the files.

Usage: ``06.2_migrate_curated.py [--write]``
"""

from collections import Counter
import json
from pathlib import Path
import sys

from lang_tools.lexicon.ingestion.spelling_reform import respell_pt
from lang_tools.lexicon.lemma_id import lemma_id

CURATED = Path("data/curated")

# file -> (text field, id field, language field or None when always pt)
FIELDS = {
    "lookalikes.jsonl": [
        ("target_text", "target_id", None),
        ("known_text", "known_id", "known_language"),
    ],
    "lookalike_worklist.jsonl": [
        ("target_text", "target_id", None),
        ("known_text", "known_id", "known_language"),
    ],
    "lookalike_gold.jsonl": [
        ("pt", "pt_lemma_id", None),
        ("other", "other_lemma_id", "other_language"),
    ],
}


def migrate(row: dict, fields: list) -> bool:
    """Respell the row's pt text fields in place; return whether one changed."""
    changed = False
    for text_key, id_key, lang_key in fields:
        if lang_key is not None and row.get(lang_key) != "pt":
            continue
        old = row[text_key]
        new = respell_pt(old)
        if new != old:
            if row[id_key] != lemma_id(old, "pt"):
                msg = f"{text_key}={old!r}: id {row[id_key]} is not the id of the text"
                raise SystemExit(msg)
            row[text_key], row[id_key] = new, lemma_id(new, "pt")
            changed = True
    return changed


write = "--write" in sys.argv
for name, fields in FIELDS.items():
    path = CURATED / name
    lines = path.read_text().splitlines()
    out, words = [], Counter()
    for line in lines:
        row = json.loads(line)
        if migrate(row, fields):
            words[row[fields[0][0]]] += 1
            # keep the file's own layout: compact or spaced separators
            spaced = line.startswith('{"') and '", "' in line
            out.append(
                json.dumps(
                    row,
                    ensure_ascii=False,
                    separators=(", ", ": ") if spaced else (",", ":"),
                )
            )
        else:
            out.append(line)
    print(f"{name}: {sum(words.values())} rows, {len(words)} words")
    if write and words:
        path.write_text("\n".join(out) + "\n")
print("written" if write else "dry run")
