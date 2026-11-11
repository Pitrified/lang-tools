"""Measure the pt form generator against kaikki and the reviewed forms (phase 1).

kaikki is read only here, from a scratch index (``{"form_of": {form: [[base,
pos, tags], ...]}, "own": {word: [[pos, gloss], ...]}}``, built from the kaikki
pt extract); the build never reads it.

Usage: ``01.1_measure_forms.py <kaikki_index.json> [floor]``
"""

from collections import Counter
import json
from pathlib import Path
import random
import sqlite3
import sys

from wordfreq import zipf_frequency

from lang_tools.lexicon.ingestion.closed_class import CLOSED_CLASS
from lang_tools.lexicon.ingestion.inflections import Reading
from lang_tools.lexicon.ingestion.inflections import analyse
from lang_tools.lexicon.ingestion.inflections import feminine
from lang_tools.lexicon.ingestion.inflections import form_note
from lang_tools.lexicon.ingestion.inflections import inflect
from lang_tools.lexicon.ingestion.inflections import participles
from lang_tools.lexicon.ingestion.inflections import pick_readings
from lang_tools.lexicon.ingestion.sense_additions import LEXFILE_POS
from lang_tools.lexicon.ingestion.sense_additions import load_sense_additions
from lang_tools.lexicon.lemma_store import LexiconStore

DATA = Path("data")
SKIP = {
    "alternative",
    "obsolete",
    "archaic",
    "misspelling",
    "nonstandard",
    "dialectal",
    "pronunciation-spelling",
    "eye-dialect",
    "rare",
    "alt-of",
}
KPOS = {"verb": "verb", "noun": "noun", "adj": "adjective"}
SAMPLE = 25


def zipf(word: str) -> float:
    """Return the pt zipf of a word."""
    return zipf_frequency(word, "pt")


def corpus() -> tuple[dict[str, set[str]], set[str]]:
    """Return the base words with their sense classes, and every pt lemma text."""
    LexiconStore.from_data_fol(DATA)  # refresh the cached store
    conn = sqlite3.connect(DATA / "lexicon/_store.sqlite")
    bases: dict[str, set[str]] = {}
    for text, lexfile in conn.execute(
        "SELECT l.text, c.lexfile FROM senses s JOIN lemmas l ON l.id = s.lemma_id"
        " JOIN concepts c ON c.id = s.concept_id"
        " WHERE l.language = 'pt' AND s.form_note IS NULL"
    ):
        pos = LEXFILE_POS.get((lexfile or "").split(".")[0])
        if pos and text.isalpha() and text.islower():
            bases.setdefault(text, set()).add(pos)
            if lexfile == "noun.person":
                bases[text].add("person")
    rows = conn.execute("SELECT text FROM lemmas WHERE language = 'pt'")
    return bases, {text for (text,) in rows}


def reviewed() -> dict[str, tuple[str, str]]:
    """Return the reviewed form words: word -> (base, label before the colon)."""
    out = {}
    for row in load_sense_additions(DATA):
        if row.language == "pt" and '"' in row.form_note:
            base = row.form_note.split('"')[1]
            out.setdefault(row.word, (base, row.form_note.split(":")[0]))
    return out


def kaikki_bases(form_of: dict, form: str, bases: dict[str, set[str]]) -> set[str]:
    """Return kaikki's bases of a form that the corpus has with the form's class.

    A base that is itself a participle form (*enviada* of *enviado*) is followed
    one step to its verb.
    """
    out = set()
    for base, pos, tags in form_of.get(form, []):
        if SKIP & set(tags):
            continue
        if KPOS.get(pos) in bases.get(base, ()):
            out.add(base)
        for deeper, _, deeper_tags in form_of.get(base, []):
            if "participle" in deeper_tags and "verb" in bases.get(deeper, ()):
                out.add(deeper)
    return out


def derived(base: str) -> set[str]:
    """Return the participles and the feminine of a base (*interessado*, *nova*)."""
    words = set(participles(base))
    words |= {w[:-1] + "a" for w in words if w.endswith("o")}
    female = feminine(base)
    return words | ({female} if female else set())


def against_kaikki(fresh: dict, form_of: dict, own: dict, bases: dict) -> None:
    """Print the model's base against kaikki's, on every model form."""
    verdict: Counter = Counter()
    examples: dict[str, list] = {}
    for form, readings in fresh.items():
        base = readings[0].base
        theirs = kaikki_bases(form_of, form, bases)
        if base in theirs:
            key = "same base" + (" (kaikki has others too)" if len(theirs) > 1 else "")
        elif any(base in derived(b) or b in derived(base) for b in theirs):
            key = "equivalent base (a participle used as a word, or a gender twin)"
        elif theirs:
            key = "other base"
        elif form in form_of:
            key = "kaikki: form of a word the corpus lacks or another class"
        elif form in own:
            key = "kaikki: a word of its own only"
        else:
            key = "kaikki: no entry"
        verdict[key] += 1
        row = (form, base, sorted(theirs), form_note(readings))
        examples.setdefault(key, []).append(row)
    print("against kaikki:")
    for key, count in verdict.most_common():
        print(f"  {key}: {count}")
        for row in random.sample(examples[key], min(SAMPLE, len(examples[key]))):
            print("     ", row)


def missed(model: dict, known: set, form_of: dict, bases: dict, floor: float) -> None:
    """Print the forms kaikki gives a corpus base that the model lacks."""
    kinds: dict[str, list] = {}
    for form, entries in form_of.items():
        if form in model or form in known or not (form.isalpha() and form.islower()):
            continue
        theirs = kaikki_bases(form_of, form, bases)
        if not theirs or zipf(form) < floor:
            continue
        kind = next(
            (pos for base, pos, _ in entries if base in theirs), "participle chain"
        )
        kinds.setdefault(kind, []).append((form, sorted(theirs)))
    print("kaikki forms the model lacks:", {k: len(v) for k, v in kinds.items()})
    for kind, rows in kinds.items():
        print(f"  {kind}:", random.sample(rows, min(60, len(rows))))


def conflicts(fresh: dict, form_of: dict, bases: dict) -> None:
    """Print the forms several bases give with a strong reading each."""
    every: dict[str, list[Reading]] = {}
    for base, classes in bases.items():
        for pos in classes:
            for form, reading in inflect(base, pos):
                if form in fresh:
                    every.setdefault(form, []).append(reading)
    rows = []
    for form, readings in every.items():
        strong = {r.base for r in readings if not r.is_weak}
        if len(strong) > 1:
            picked = pick_readings(readings, zipf)[0].base
            theirs = kaikki_bases(form_of, form, bases)
            scores = {b: round(zipf(b), 1) for b in sorted(strong)}
            rows.append((form, picked, scores, sorted(theirs)))
    agree = sum(1 for row in rows if row[1] in row[3])
    print(
        f"forms with strong readings of several bases: {len(rows)}; kaikki agrees on {agree}"
    )
    for row in random.sample(rows, min(80, len(rows))):
        print("   ", row)


def lookalikes(fresh: dict, own: dict) -> None:
    """Print the model forms that are frequent English words or names."""
    english = sorted(
        (f for f in fresh if zipf_frequency(f, "en") >= zipf(f)),
        key=lambda f: -zipf_frequency(f, "en"),
    )
    print(f"model forms as frequent in English: {len(english)}", english[:80])
    names = sorted(
        f for f in fresh if any(p == "name" for p, _ in own.get(f.capitalize(), []))
    )
    print(f"model forms that are also names: {len(names)}", names[:80])
    words = sorted(f for f in fresh if f in own)
    print(f"model forms that are also a word of their own: {len(words)}")


def against_reviewed(model: dict, gold: dict) -> None:
    """Print the model's base against the reviewed rows' base."""
    closed = CLOSED_CLASS["pt"]
    agree: Counter = Counter()
    rows = []
    for word, (base, label) in sorted(gold.items()):
        if word in closed:
            agree["closed-class word (left to its row)"] += 1
            continue
        readings = model.get(word)
        if readings is None:
            agree["no model form"] += 1
            rows.append((word, base, None, label, None))
            continue
        ours = readings[0].base
        agree["same base" if ours == base else "other base"] += 1
        if ours != base:
            rows.append((word, base, ours, label, form_note(readings)))
    print("reviewed form words:", dict(agree))
    for row in rows:
        print("   ", row)


def main() -> None:
    """Print every measure."""
    index = json.loads(Path(sys.argv[1]).read_text())
    form_of, own = index["form_of"], index["own"]
    floor = float(sys.argv[2]) if sys.argv[2:] else 3.0
    random.seed(0)
    bases, texts = corpus()
    gold = reviewed()
    known = (texts | CLOSED_CLASS["pt"]) - set(gold)
    model = analyse(bases, known=known, zipf=zipf, floor=floor)
    fresh = {f: r for f, r in model.items() if f not in gold}
    print(
        f"floor {floor}: {len(fresh)} model forms (plus {len(model) - len(fresh)} reviewed)"
    )
    print("  by class:", Counter(r[0].part_of_speech for r in fresh.values()))
    against_kaikki(fresh, form_of, own, bases)
    missed(model, known, form_of, bases, floor)
    conflicts(fresh, form_of, bases)
    lookalikes(fresh, own)
    against_reviewed(model, gold)


main()
