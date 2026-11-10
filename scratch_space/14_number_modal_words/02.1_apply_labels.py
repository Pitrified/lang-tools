"""Apply a 14_number_modal_words labels file through the hand-correction calls.

A labels file is tab-separated, one action per line:
``add|pin|drop|skip, word, key, form note, reason``. With ``--dry`` every line
is checked against the built corpus and nothing is written; a real run writes
the rows only when the dry check passes for every line.

Usage: ``02.1_apply_labels.py [--dry] <labels file>...``
"""

from pathlib import Path
import sys

from lang_tools.lexicon.ingestion.closed_class import CLOSED_CLASS
from lang_tools.lexicon.ingestion.sense_review import _options
from lang_tools.lexicon.ingestion.sense_review import add_sense
from lang_tools.lexicon.ingestion.sense_review import drop_sense
from lang_tools.lexicon.ingestion.sense_review import pin_sense
from lang_tools.lexicon.lemma_id import lemma_id
from lang_tools.lexicon.lemma_store import get_store
from lang_tools.params.lang_tools_params import get_lang_tools_params

LANGUAGE = "pt"

args = sys.argv[1:]
dry = "--dry" in args
files = [Path(a) for a in args if a != "--dry"]
store = get_store()
data_fol = get_lang_tools_params().paths.data_fol

lines = []
for path in files:
    for raw in path.read_text().splitlines():
        if raw.strip():
            action, word, key, note, reason = (raw.split("\t") + [""] * 5)[:5]
            # A note may come in the rulebook's batch braces: {note}.
            note = note.strip().removeprefix("{").removesuffix("}")
            lines.append((path.name, action, word, key, note, reason))

# pin and drop check the built corpus only, as the calls themselves do.
problems = []
for name, action, word, key, _note, _reason in lines:
    target = lemma_id(word, LANGUAGE)
    known = {o.concept_key for o in _options(store, target)}
    if action == "add":
        if store.get_concept_by_key(key) is None:
            problems.append(f"{name}: add {word}: no concept {key}")
        if word.lower() in CLOSED_CLASS[LANGUAGE]:
            problems.append(f"{name}: add {word}: closed-class")
    elif action in {"pin", "drop"}:
        if key not in known:
            problems.append(f"{name}: {action} {word}: no sense {key}")
    elif action != "skip":
        problems.append(f"{name}: unknown action {action!r} for {word}")

counts: dict[str, int] = {}
for _name, action, *_ in lines:
    counts[action] = counts.get(action, 0) + 1
print(len(lines), "lines", counts)
print("\n".join(problems) or "no problems")
if dry or problems:
    sys.exit(1 if problems else 0)

for _name, action, word, key, note, reason in lines:
    if action == "add":
        add_sense(data_fol, store, word, LANGUAGE, key, reason=reason, form_note=note)
    elif action == "drop":
        drop_sense(data_fol, store, word, LANGUAGE, key, reason=reason)
    elif action == "pin":
        pin_sense(data_fol, store, word, LANGUAGE, key)
print("applied")
