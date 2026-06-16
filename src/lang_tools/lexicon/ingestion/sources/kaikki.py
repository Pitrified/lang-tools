"""kaikki.org (Wiktionary) source adapter - the enrichment layer.

OMW gloss and example coverage is uneven across the non-English languages. kaikki
publishes per-language JSONL with rich glosses and example sentences; this module
parses that JSONL into a small `KaikkiEntry` keyed by ``(normalized text,
language)`` so `transform` can join it onto the OMW backbone and fill sparse
`Concept.definitions` and `Lemma.examples`.

It does **not** introduce new concepts or lemmas: kaikki is enrichment only and
carries a CC-BY-SA (share-alike) license, so anything it contributes is tagged
``source=kaikki`` and stays license-isolated (phase 10). Parsing reuses the
existing `WikiRecord` / `WikiSense` shapes from `wiktionary.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
import json
from typing import IO
from typing import TYPE_CHECKING

from lang_tools.language.normalization import normalize
from lang_tools.lexicon.ingestion.wiktionary import WikiRecord
from lang_tools.lexicon.lemma import LemmaExample

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@dataclass
class KaikkiEntry:
    """Enrichment payload for one Wiktionary headword in one language.

    Attributes:
        text: The headword as written (accents preserved).
        language: ISO 639-1 code stamped by the caller.
        definitions: Gloss strings gathered across the record's senses.
        examples: Curated example sentences (with optional translation).
    """

    text: str
    language: str
    definitions: list[str] = field(default_factory=list)
    examples: list[LemmaExample] = field(default_factory=list)

    @property
    def key(self) -> tuple[str, str]:
        """Join key onto the OMW backbone: ``(normalized text, language)``."""
        return (normalize(self.text), self.language)


def _iter_jsonl(source: Path | IO[str]) -> Iterator[str]:
    if hasattr(source, "read"):  # an open text stream
        yield from source  # type: ignore[union-attr]
    else:
        with source.open("r", encoding="utf-8") as fh:  # type: ignore[union-attr]
            yield from fh


def _record_to_entry(record: WikiRecord, language: str) -> KaikkiEntry:
    definitions: list[str] = []
    examples: list[LemmaExample] = []
    for sense in record.senses:
        for gloss in sense.glosses:
            if gloss and gloss not in definitions:
                definitions.append(gloss)
        for raw in sense.examples:
            sentence = raw.get("text") or raw.get("example")
            if not sentence:
                continue
            translation = raw.get("english") or raw.get("translation")
            examples.append(LemmaExample(sentence=sentence, translation=translation))
    return KaikkiEntry(
        text=record.word,
        language=language,
        definitions=definitions,
        examples=examples,
    )


def load_kaikki_entries(
    source: Path | IO[str],
    language: str,
) -> Iterator[KaikkiEntry]:
    """Yield `KaikkiEntry` enrichment records from a kaikki.org JSONL dump.

    Unlike `load_wiktionary_jsonl` (which builds thin `Lemma`s and drops glosses),
    this keeps the glosses and example sentences - the whole point of the
    enrichment layer. Records with no headword are skipped; malformed lines are
    ignored so a partial dump still loads.

    Args:
        source: Filesystem path or open text stream of kaikki JSONL.
        language: ISO 639-1 code to stamp on every produced entry.

    Yields:
        One `KaikkiEntry` per parsable record that has a headword.
    """
    for raw_line in _iter_jsonl(source):
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        record = WikiRecord.model_validate(payload)
        if not record.word:
            continue
        yield _record_to_entry(record, language)
