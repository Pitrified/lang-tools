"""User-progress tracking and weighted word selection.

Public API:
    UserWordProgress: per-user per-word performance record.
    ExerciseStats: per-exercise-type breakdown of progress.
    WordFilter: optional pool filter for `select_words`.
    SelectionWeights: tunable weighting factors.
    select_words: weighted random selection over a `Word` pool.
    compute_weight: pure scoring function used by the selector.
"""

from lang_tools.progress.progress import ExerciseStats
from lang_tools.progress.progress import UserWordProgress
from lang_tools.progress.selection import SelectionWeights
from lang_tools.progress.selection import WordFilter
from lang_tools.progress.selection import compute_weight
from lang_tools.progress.selection import select_words

__all__ = [
    "ExerciseStats",
    "SelectionWeights",
    "UserWordProgress",
    "WordFilter",
    "compute_weight",
    "select_words",
]
