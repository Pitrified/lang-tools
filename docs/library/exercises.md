# Exercises

The `lang_tools.exercises` package implements the five exercise mechanics
unified from the upstream apps. Each exercise follows the same shape:

1. Construct an exercise instance (optionally passing an RNG and a
   `progress_callback`).
2. Call `start(...)` to obtain an `ExerciseRound`.
3. Call `submit(round_, user_input)` repeatedly, receiving `RoundResult`
   instances. The callback receives `WordResult` lists when a word is
   considered "consumed".
4. Call `finish()` for a `SessionSummary`.

The `ExerciseType` literal enumerates the five mechanics:

```python
from lang_tools.exercises import EXERCISE_TYPES
print(EXERCISE_TYPES)
# ('sentence_reconstruction', 'pair_matching', 'diacritic_typing',
#  'wordle', 'conversational_tutor')
```

## Sentence reconstruction

Show the user a translation and a shuffled list of word portions from the
target sentence. They must reorder the portions back into the sentence.
Powered by [`SentenceReconstructionExercise`](../reference/lang_tools/exercises/sentence_reconstruction/);
short portions (less than three characters) are merged into their neighbour
via `merge_short_portions`.

## Pair matching

Given N words, the user matches each one to its translation drawn from a
shuffled column. Each `submit` call evaluates a single
`(left, right)` tap. Raises
[`MissingTranslationError`](../reference/lang_tools/exercises/pair_matching/)
if a word lacks the requested target language.

## Diacritic typing

The user types a hidden accented word character by character. Each `submit`
evaluates one keystroke; correct characters are revealed, wrong keys are
added to a disabled set. Three hint levels (`off`, `show_unaccented`,
`show_all`) control how much is revealed at the start.

## Wordle

Guess a hidden word in `len(word) + 1` attempts. After each guess each
letter receives a state of `correct`, `misplaced`, `wrong`, or `unused`. A
keyboard map is maintained for the UI.

## Conversational tutor

The loosely-coupled exercise: the caller supplies a `chain` callable
(typically wired to `lang_tools.llm.tutor.build_tutor_chain`) and the
exercise just appends user / tutor messages to a `TutorMessage` history.
Word-level progress falls out of analysing the tutor correction blocks.
