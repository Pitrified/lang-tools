"""Measure the pinned part of speech on a fresh build (phase 1).

The lemmas whose part of speech changed against a snapshot taken before the
build (``{lemma_id: [language, text, pos]}`` as JSON), and, for the unpinned
lemmas, how many have a part of speech other than the class of their card
sense, by `wordfreq` band of the pt word (Q4, assessed only).

Usage: ``01.1_measure_pos.py <snapshot.json> [--list]``
"""

from collections import Counter
import json
from pathlib import Path
import sqlite3
import sys

import pyarrow.parquet as pq
from wordfreq import top_n_list

from lang_tools.lexicon.ingestion.sense_additions import LEXFILE_POS
from lang_tools.lexicon.lemma_store import LexiconStore

DATA = Path("data")
BANDS = (1_000, 5_000, 20_000)


def changed(snapshot: dict) -> list[tuple]:
    """Return ``(language, text, old, new)`` for every lemma whose class changed."""
    out = []
    for lang in ("pt", "en", "es", "fr", "it"):
        table = pq.read_table(
            DATA / f"lexicon/lemmas/{lang}.parquet",
            columns=["id", "text", "part_of_speech"],
        )
        for row in table.to_pylist():
            old = snapshot.get(row["id"])
            if old is not None and old[2] != row["part_of_speech"]:
                out.append((lang, row["text"], old[2], row["part_of_speech"]))
    return out


def unpinned_mismatch() -> dict[str, list[tuple]]:
    """Return the unpinned pt lemmas whose class is not their card's, by band."""
    LexiconStore.from_data_fol(DATA)  # refresh the cached store
    conn = sqlite3.connect(DATA / "lexicon/_store.sqlite")
    rows = conn.execute(
        """
SELECT l.text, d.part_of_speech, c.lexfile
  FROM lemma_drill d
  JOIN lemmas l ON l.id = d.lemma_id
  JOIN concepts c ON c.id = d.concept_id
 WHERE d.language = 'pt'
   AND NOT EXISTS (SELECT 1 FROM senses s
                    WHERE s.lemma_id = d.lemma_id AND s.is_best = 1)
"""
    ).fetchall()
    rank = {w: i for i, w in enumerate(top_n_list("pt", BANDS[-1]))}
    out: dict[str, list[tuple]] = {}
    for text, pos, lexfile in rows:
        card = LEXFILE_POS.get((lexfile or "").split(".")[0])
        i = rank.get(text)
        band = next((f"top {b:,}" for b in BANDS if i is not None and i < b), "rest")
        out.setdefault(band, [])
        if card is not None and card != pos:
            out[band].append((text, pos, card))
        out.setdefault(f"{band} total", []).append(text)
    return out


def main() -> None:
    """Print the counts, and the changed lemmas with ``--list``."""
    snapshot = json.loads(Path(sys.argv[1]).read_text())
    rows = changed(snapshot)
    print("changed:", len(rows), Counter(r[0] for r in rows))
    print(Counter((r[2], r[3]) for r in rows).most_common())
    bands = unpinned_mismatch()
    for band in (*(f"top {b:,}" for b in BANDS), "rest"):
        bad = bands.get(band, [])
        total = len(bands.get(f"{band} total", []))
        print(f"unpinned pt {band}: {len(bad)} of {total} differ", bad[:15])
    if "--list" in sys.argv:
        for row in rows:
            print("\t".join(str(v) for v in row))


main()
