"""Wiktionary JSONL ingestion (kaikki.org dumps -> `Lemma`).

A line in a kaikki.org JSONL file is one `WikiRecord`. This module parses such
records and maps the relevant fields onto the unified `Lemma` schema. Filtering
options follow the suggestions in
``linux-box-cloudflare/scratch_space/vibes/10-language-overview/06-word-ingestion.md``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import IO
from typing import TYPE_CHECKING

from pydantic import BaseModel
from pydantic import Field

from lang_tools.lexicon.lemma import Lemma

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Iterator

_DEFAULT_KEEP_POS: frozenset[str] = frozenset(
    {"noun", "verb", "adjective", "adverb", "expression", "phrase", "intj"},
)


class WikiSense(BaseModel):
    """One sense entry inside a kaikki.org Wiktionary record.

    Attributes:
        glosses: List of definition strings.
        raw_glosses: Raw (uncleaned) gloss strings.
        examples: List of example dicts ``{"text": ..., "english": ...}``.
        categories: Wiktionary category tags.
        tags: Per-sense tag list (e.g. ``["transitive"]``).
        topics: Topic tags.
    """

    glosses: list[str] = Field(default_factory=list)
    raw_glosses: list[str] = Field(default_factory=list)
    examples: list[dict] = Field(default_factory=list)
    categories: list[dict] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)


class WikiRecord(BaseModel):
    """One line of a kaikki.org Wiktionary JSONL dump.

    Attributes:
        word: The headword.
        pos: Part of speech.
        senses: List of senses.
        categories: Top-level category tags.
        form_of: Lemma references when this entry is an inflected form.
    """

    word: str
    pos: str | None = None
    senses: list[WikiSense] = Field(default_factory=list)
    categories: list[dict] = Field(default_factory=list)
    form_of: list[dict] = Field(default_factory=list)

    model_config = {"extra": "ignore"}


def _record_to_lemma(record: WikiRecord, language: str) -> Lemma:
    # Glosses are no longer stored on the thin `Lemma`; they become per-language
    # `Concept.definitions` during concept mapping (phase 5). Here we keep only
    # the token fields. `WikiSense` is still parsed so phase 5 can read senses.
    return Lemma(
        text=record.word,
        language=language,
        part_of_speech=record.pos,
        sources=["wiktionary"],
    )


def _iter_jsonl(source: Path | IO[str]) -> Iterator[str]:
    if isinstance(source, Path):
        with source.open("r", encoding="utf-8") as fh:
            yield from fh
    else:
        yield from source


def load_wiktionary_jsonl(
    source: Path | IO[str],
    language: str,
    *,
    keep_pos: Iterable[str] | None = _DEFAULT_KEEP_POS,
    require_accent: bool = False,
    skip_form_of: bool = True,
) -> Iterator[Lemma]:
    """Yield `Lemma` objects parsed from a kaikki.org JSONL file.

    Args:
        source: Filesystem path or open text stream.
        language: ISO 639-1 code to stamp on every produced `Lemma`.
        keep_pos: Allowed part-of-speech values; pass ``None`` to keep all.
        require_accent: If True, only yield lemmas with at least one diacritic.
        skip_form_of: If True, skip entries that are inflected-form pointers.

    Yields:
        `Lemma` instances for records that pass every filter.
    """
    keep = frozenset(keep_pos) if keep_pos is not None else None
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
        if skip_form_of and record.form_of:
            continue
        if keep is not None and (record.pos or "").lower() not in keep:
            continue
        lemma = _record_to_lemma(record, language)
        if require_accent and not lemma.has_accent:
            continue
        yield lemma
