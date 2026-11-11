"""Check the generated forms of a fresh build against their bases (phase 2).

For every lemma the inflection stage created: its card shows its base's card
concept (or, when the base's card is of another class, a concept of the form's
class), its note names its base, and its part of speech is a class of its
senses. Prints the counts, every exception, and a random sample of cards to
read; with a kaikki index (see ``01.1_measure_forms.py``) also lists the forms
that are a word of their own there.

Usage: ``02.1_check_forms.py [sample] [kaikki_index.json]``
"""

from collections import Counter
import json
from pathlib import Path
import random
import sqlite3
import sys

from lang_tools.lexicon.lemma_id import lemma_id
from lang_tools.lexicon.lemma_store import LexiconStore

DATA = Path("data")


def main() -> None:
    """Print the checks."""
    size = int(sys.argv[1]) if sys.argv[1:] else 500
    store = LexiconStore.from_data_fol(DATA)
    conn = sqlite3.connect(DATA / "lexicon/_store.sqlite")
    conn.row_factory = sqlite3.Row
    forms = conn.execute(
        "SELECT l.id, l.text, l.part_of_speech, d.concept_id, d.form_note, d.cefr_level"
        " FROM lemmas l JOIN lemma_drill d ON d.lemma_id = l.id"
        " WHERE l.language = 'pt' AND l.sources LIKE '%inflection%'"
    ).fetchall()
    cards = {
        row["lemma_id"]: row["concept_id"]
        for row in conn.execute("SELECT lemma_id, concept_id FROM lemma_drill")
    }
    verdict: Counter = Counter()
    exceptions: dict[str, list] = {}
    for row in forms:
        base = (row["form_note"] or '"?"').split('"')[1]
        base_card = cards.get(lemma_id(base, "pt"))
        senses = {s.concept_id for s in store.senses_for_lemma(row["id"])}
        if base_card == row["concept_id"]:
            key = "card is the base's card"
        elif base_card not in senses:
            key = "base card is of another class; card is a base sense of the form's class"
        else:
            key = "card differs from the base's card"
        verdict[key] += 1
        exceptions.setdefault(key, []).append(
            (row["text"], base, row["concept_id"], base_card)
        )
    print(f"{len(forms)} generated pt forms")
    for key, count in verdict.most_common():
        print(f"  {key}: {count}")
        if key != "card is the base's card":
            print("     ", exceptions[key][:30])
    print(
        "  by band:",
        sorted(Counter(row["cefr_level"] for row in forms).items(), key=str),
    )
    print("  by part of speech:", Counter(row["part_of_speech"] for row in forms))

    random.seed(1)
    print(f"sample of {size}:")
    for row in random.sample(forms, min(size, len(forms))):
        card = store.lemma_card(row["id"], translation_languages=["en"])
        if card is None:
            print("   no card:", row["text"])
            continue
        translations = ", ".join(card.translations.get("en", [])[:3])
        print(f"   {row['text']:16} {card.form_note} | {translations} | {card.gloss}")

    if sys.argv[2:]:
        own = json.loads(Path(sys.argv[2]).read_text())["own"]
        words = sorted(row["text"] for row in forms if row["text"] in own)
        print(f"forms that are a word of their own in kaikki: {len(words)}")
        print(" ".join(words))


main()
