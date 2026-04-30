# Progress and selection

The `lang_tools.progress` package tracks per-user progress on each word and
turns that progress into a weighted random sampler over a pool.

## `UserWordProgress`

Each `(user_id, word_id)` pair has its own `UserWordProgress` record holding
overall counters, per-exercise `ExerciseStats`, and a `is_useless` flag for
words the user wants to exclude.

```python
from lang_tools.progress import UserWordProgress

p = UserWordProgress(user_id="alice", word_id="abcd1234")
p.record(correct=True, exercise_type="wordle")
p.exercise_stats["wordle"].correct_count   # 1
```

## Weighted selection

`compute_weight(word, progress, weights)` is the primitive: it returns 0 for
useless words and otherwise blends an unseen / error / frequency / recency
score. `select_words(pool, progress, n, ...)` performs weighted sampling
without replacement.

```python
import random
from lang_tools.progress import select_words, WordFilter, SelectionWeights

chosen = select_words(
    pool,
    progress_lookup,
    n=5,
    word_filter=WordFilter(min_length=4, has_accent=True),
    weights=SelectionWeights(error_boost=4.0),
    rng=random.Random(0),
)
```

The defaults reproduce the heuristics used in `brazilian-bites` and
`go-accenter`: errors strongly increase the next-pick weight, unseen words
get the maximum priority, high-frequency words get a mild bonus, and
recently-seen words decay over a configurable half-life.
