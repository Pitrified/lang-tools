"""Exercise framework: shared interface and per-mechanic implementations.

Public API:
    EXERCISE_TYPES: tuple of supported exercise type strings.
    ExerciseType: literal alias.
    ExerciseRound, RoundResult, WordResult, SessionSummary: shared data shapes.
    SentenceReconstructionExercise, PairMatchingExercise,
    DiacriticTypingExercise, WordleExercise, ConversationalTutorExercise:
    concrete exercise classes.
    HintLevel: literal for diacritic-typing hint levels.
"""

from lang_tools.exercises.base import EXERCISE_TYPES
from lang_tools.exercises.base import ExerciseRound
from lang_tools.exercises.base import ExerciseType
from lang_tools.exercises.base import RoundResult
from lang_tools.exercises.base import SessionSummary
from lang_tools.exercises.base import WordResult
from lang_tools.exercises.conversational_tutor import ConversationalTutorExercise
from lang_tools.exercises.conversational_tutor import TutorMessage
from lang_tools.exercises.diacritic_typing import DiacriticTypingExercise
from lang_tools.exercises.diacritic_typing import HintLevel
from lang_tools.exercises.pair_matching import PairMatchingExercise
from lang_tools.exercises.sentence_reconstruction import SentenceReconstructionExercise
from lang_tools.exercises.wordle import LetterResult
from lang_tools.exercises.wordle import LetterState
from lang_tools.exercises.wordle import WordleExercise

__all__ = [
    "EXERCISE_TYPES",
    "ConversationalTutorExercise",
    "DiacriticTypingExercise",
    "ExerciseRound",
    "ExerciseType",
    "HintLevel",
    "LetterResult",
    "LetterState",
    "PairMatchingExercise",
    "RoundResult",
    "SentenceReconstructionExercise",
    "SessionSummary",
    "TutorMessage",
    "WordResult",
    "WordleExercise",
]
