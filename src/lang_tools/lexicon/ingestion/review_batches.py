"""Shared plumbing of the agent batch reviews (look-alikes, card senses).

Each review reserves its batches as JSONL files under a work folder of its own
(``data/work/<review>/``, not committed), serialises reservations and applies
with a file lock, so parallel reviewers never get the same items, and hashes its
rulebook into every row it writes, so a rule change is visible in the data.
"""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from collections.abc import Sequence
    from pathlib import Path

    from pydantic import BaseModel


class LabelError(ValueError):
    """The reviewer's labels for a batch do not validate."""

    def __init__(self, batch: str, problems: Sequence[str]) -> None:
        """Keep the problems, and list them in the message."""
        self.problems = list(problems)
        super().__init__(
            f"batch {batch}: {len(self.problems)} problem(s): "
            + "; ".join(self.problems)
        )


def guide_sha(guide_path: Path) -> str:
    """Return a short hash of the review guide, for provenance."""
    return (
        hashlib.sha256(guide_path.read_bytes()).hexdigest()[:12]
        if guide_path.exists()
        else ""
    )


def work_dir(data_fol: Path, subdir: str) -> Path:
    """Return (and create) a review's work folder under the data folder."""
    path = data_fol / subdir
    path.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def locked(data_fol: Path, subdir: str) -> Iterator[None]:
    """Serialize reservations and applies across concurrent reviewers."""
    with (work_dir(data_fol, subdir) / ".lock").open("w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def append_rows(path: Path, rows: Sequence[BaseModel]) -> None:
    """Append rows to a JSONL file, creating it and its folder if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.writelines(row.model_dump_json() + "\n" for row in rows)
