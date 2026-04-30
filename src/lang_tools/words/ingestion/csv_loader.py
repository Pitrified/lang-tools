"""CSV ingestion for `brazilian-bites` style vocabulary files."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import IO
from typing import TYPE_CHECKING
from typing import cast

from lang_tools.words.word import FalseFriend
from lang_tools.words.word import FrequencyLevel
from lang_tools.words.word import Word
from lang_tools.words.word import WordExample

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Iterator

_CSV_REQUIRED: frozenset[str] = frozenset({"text", "language"})
_FREQUENCY_VALUES: frozenset[str] = frozenset({"high", "medium", "low"})


class CSVColumnsMissingError(ValueError):
    """Raised when a CSV is missing required columns."""

    def __init__(self, missing: Iterable[str]) -> None:
        """Initialize with the offending column names.

        Args:
            missing: Iterable of column names that were expected.
        """
        cols = sorted(missing)
        super().__init__(f"CSV missing required columns: {cols}")
        self.missing = cols


def _split_topics(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [t.strip() for t in raw.split(",") if t.strip()]


def _row_to_word(row: dict[str, str]) -> Word:
    text = row["text"].strip()
    language = row["language"].strip().lower()

    translations: dict[str, str] = {}
    for key, value in row.items():
        if key.startswith("translation_") and value:
            translations[key.removeprefix("translation_")] = value.strip()

    topics = _split_topics(row.get("topics") or row.get("topic"))
    if row.get("secondary_topics"):
        topics.extend(_split_topics(row["secondary_topics"]))

    freq_raw = (row.get("frequency") or "").strip().lower()
    frequency: FrequencyLevel | None = (
        cast("FrequencyLevel", freq_raw) if freq_raw in _FREQUENCY_VALUES else None
    )

    examples: list[WordExample] = []
    if row.get("example_sentence"):
        examples.append(
            WordExample(
                sentence=row["example_sentence"].strip(),
                translation=(row.get("example_translation") or "").strip() or None,
            ),
        )

    false_friends: list[FalseFriend] = []
    if row.get("false_friend_language") and row.get("false_friend_word"):
        score_raw = (row.get("false_friend_similarity") or "").strip()
        false_friends.append(
            FalseFriend(
                language=row["false_friend_language"].strip().lower(),
                similar_word=row["false_friend_word"].strip(),
                similarity_score=float(score_raw) if score_raw else None,
                actual_meaning=(row.get("false_friend_meaning") or "").strip(),
            ),
        )

    return Word(
        text=text,
        language=language,
        part_of_speech=(row.get("part_of_speech") or "").strip() or None,
        frequency=frequency,
        translations=translations,
        topics=topics,
        examples=examples,
        false_friends=false_friends,
        sources=["csv"],
    )


def _iter_rows(source: Path | IO[str]) -> Iterator[dict[str, str]]:
    if isinstance(source, Path):
        with source.open("r", encoding="utf-8", newline="") as fh:
            yield from csv.DictReader(fh)
    else:
        yield from csv.DictReader(source)


def load_csv(source: Path | IO[str]) -> Iterator[Word]:
    """Yield `Word` objects parsed from a vocabulary CSV.

    The CSV must contain at least ``text`` and ``language`` columns. Optional
    columns include:

    - ``part_of_speech``, ``frequency`` (``high``/``medium``/``low``)
    - ``topics`` and ``secondary_topics`` (comma-separated)
    - ``translation_<lang>`` (one column per target language)
    - ``example_sentence`` + ``example_translation``
    - ``false_friend_language``, ``false_friend_word``, ``false_friend_meaning``,
      ``false_friend_similarity``

    Args:
        source: Path to the CSV file or an already-open text stream.

    Yields:
        Parsed `Word` instances.

    Raises:
        CSVColumnsMissingError: If the header does not contain the required columns.
    """
    rows = _iter_rows(source)
    try:
        first = next(rows)
    except StopIteration:
        return
    missing = _CSV_REQUIRED - first.keys()
    if missing:
        raise CSVColumnsMissingError(missing)
    yield _row_to_word(first)
    for row in rows:
        yield _row_to_word(row)
