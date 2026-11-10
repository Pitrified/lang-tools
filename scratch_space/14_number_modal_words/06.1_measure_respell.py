"""Measure the pre-reform respelling on the built pt lemmas (phase 6).

The lemmas `respell_pt` touches, how many a frequency gate would let through
(the modern spelling more frequent in `wordfreq` than the old one), how many
have the modern spelling as a lemma already, and the curated rows keyed on an
old lemma id. Run it on a corpus built before the respelling.

Usage: ``06.1_measure_respell.py [--list]``
"""

from collections import Counter
import json
from pathlib import Path
import sys

import pyarrow.parquet as pq
from wordfreq import zipf_frequency

from lang_tools.lexicon.ingestion.spelling_reform import respell_pt
from lang_tools.lexicon.lemma_id import lemma_id

LEMMAS = Path("data/lexicon/lemmas/pt.parquet")
CURATED = Path("data/curated")
FREQUENT = 3.0


def main() -> None:
    """Print the counts, and every respelt lemma with ``--list``."""
    texts = sorted(set(pq.read_table(LEMMAS, columns=["text"])["text"].to_pylist()))
    present = set(texts)
    rows = [
        (old, new, zipf_frequency(old, "pt"), zipf_frequency(new, "pt"))
        for old in texts
        if (new := respell_pt(old)) != old
    ]
    print(len(texts), "pt lemmas;", len(rows), "respelt")
    print(
        "modern more frequent",
        sum(1 for r in rows if r[3] > r[2]),
        "; tie",
        sum(1 for r in rows if r[3] == r[2]),
        "; old more frequent",
        sum(1 for r in rows if r[3] < r[2]),
    )
    print("modern spelling already a lemma:", sum(1 for r in rows if r[1] in present))
    print("modern above zipf 3:", sum(1 for r in rows if r[3] >= FREQUENT))

    old_ids = {lemma_id(r[0], "pt") for r in rows}
    keyed: Counter[str] = Counter()
    for path in sorted(CURATED.glob("*.jsonl")):
        for line in path.read_text().splitlines():
            values = json.loads(line).values()
            if any(isinstance(v, str) and v in old_ids for v in values):
                keyed[path.name] += 1
    print("curated rows keyed on an old lemma:", dict(keyed))

    if "--list" in sys.argv:
        for old, new, zo, zn in rows:
            flag = "BOTH" if new in present else ""
            print(f"{old}\t{new}\t{zo:.2f}\t{zn:.2f}\t{flag}")


main()
