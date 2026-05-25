# Exercise Wiring Status

Status of each exercise: API endpoint, frontend JS, and what's still missing.

## Summary

| Exercise | API | JS | Working E2E? | Missing |
|----------|-----|----|-------------|---------|
| Pair Matching | start + submit | wired | Yes | - |
| Wordle | start + guess | wired | Yes | CSS classes for `wordle-tile-misplaced` |
| Diacritic Typing | start + keystroke | wired | Yes | Accent key list is hardcoded PT only |
| Sentence Reconstruction | start + submit | wired | Yes | - |
| Conversational Tutor | message | wired | Placeholder | Needs LLM integration |

## Architecture

```
Browser JS  -->  /api/v1/exercises/<game>/<action>  -->  exercises_api.py
                                                            |
                                                    Exercise library class
                                                    (start -> ExerciseRound)
                                                    (submit -> RoundResult)
                                                            |
                                                    word_store.get_words_filtered()
                                                    (loads from data/bootstrap/*.csv)
```

- `ExerciseRound` stores state in `prompt` (client-visible) and `expected` (server-only).
- In-memory `_active_rounds` dict keyed by `{user_id}:{game_type}` holds active games.
- Auth is dev-bypass (hardcoded user) in dev mode, cookie session in prod.

## Per-Exercise Detail

### 1. Pair Matching

**API endpoints:**
- `POST /api/v1/exercises/pair-matching/start` - picks N random words with translations, returns shuffled left/right columns
- `POST /api/v1/exercises/pair-matching/submit` - evaluates a single (left, right) pair

**JS (`static/js/pair_matching.js`):**
- Renders left/right button columns from start response
- Click-to-select on each side, auto-submits when both selected
- Colors matched pairs green, shows feedback for wrong matches

**Missing:** Nothing critical. Could add "all matched" celebration.

### 2. Wordle

**API endpoints:**
- `POST /api/v1/exercises/wordle/start` - picks random word of requested length, returns `word_length` and `max_attempts`
- `POST /api/v1/exercises/wordle/guess` - evaluates guess, returns per-letter results (correct/misplaced/wrong), keyboard state, finished flag

**JS (`static/js/wordle.js`):**
- Grid board + on-screen keyboard
- Submits guess to API, colors tiles per response
- Updates keyboard key colors
- Shows win/loss message with answer

**CSS (`static/css/wordle.css`):**
- Has `wordle-tile-correct` (green) and `wordle-tile-wrong` (grey)
- **Missing:** `wordle-tile-misplaced` class (yellow) and keyboard color classes (`wordle-key-correct`, `wordle-key-misplaced`, `wordle-key-wrong`)

**Missing:** Add missing CSS color classes to `wordle.css`.

### 3. Diacritic Typing

**API endpoints:**
- `POST /api/v1/exercises/diacritic-typing/start` - picks random accented word, returns display array (underscores for hidden chars), translation
- `POST /api/v1/exercises/diacritic-typing/keystroke` - evaluates one character, returns updated display, errors, finished flag

**JS (`static/js/diacritic_typing.js`):**
- Shows char-by-char display with cursor highlight
- On-screen accent keyboard (hardcoded PT accents: á à â ã é ê í ó ô õ ú ç)
- Disables wrong keys client-side
- Shows completion message with error count

**Missing:**
- Accent key list should be dynamic per language (currently hardcoded Portuguese)
- No base keyboard rendering after start (only accent keys shown)
- Template needs a `<div id="word-translation">` and `<div id="diacritic-message">` elements

### 4. Sentence Reconstruction

**API endpoints:**
- `POST /api/v1/exercises/sentence-reconstruction/start` - picks word with example sentence, returns shuffled portions + translation hint
- `POST /api/v1/exercises/sentence-reconstruction/submit` - evaluates ordering, returns correct flag + answer if wrong

**JS (`static/js/sentence_reconstruction.js`):**
- Renders shuffled portions as clickable buttons
- Builds reconstructed sentence as user clicks
- Auto-submits when all portions selected
- Shows correct/incorrect with answer

**Missing:** Nothing critical. Could add "undo last" button.

### 5. Conversational Tutor

**API endpoint:**
- `POST /api/v1/exercises/conversational-tutor/message` - returns placeholder text (LLM not connected)

**JS (`static/js/conversational_tutor.js`):**
- Chat bubble UI with user/tutor messages
- Handles correction vs content response types
- Already fully wired, just needs LLM backend

**Missing:**
- LLM integration (needs `llm-core` StructuredLLMChain for tutor correction)
- Topic suggestion
- Session history persistence

## Global Issues Fixed This Session

1. **404 on exercise APIs** - exercises_api router had prefix `/api/v1/exercises` but was nested under api_router with prefix `/api/v1`, giving double prefix. Fixed to `/exercises`.
2. **Pyright errors** - API code accessed `round_.pairs`, `round_.max_attempts` etc. directly, but `ExerciseRound` only has `prompt` (dict) and `expected`. Fixed to use `round_.prompt[...]`.
3. **422 Unprocessable Content** - `SessionData` was imported under `TYPE_CHECKING` but used in `Annotated[SessionData, Depends(...)]`. With `from __future__ import annotations`, FastAPI couldn't resolve the type at runtime. Fixed by moving import out of `TYPE_CHECKING` block (with `# noqa: TC002`).
4. **"No accented words"** - was a downstream effect of the 422; the JS fallback message showed when the API failed.

## What's Needed for Full Production

1. **Wordle CSS** - add `wordle-tile-misplaced` (yellow) and keyboard color classes
2. **Diacritic template** - ensure `#word-translation` and `#diacritic-message` divs exist in template
3. **Language selector** - all exercises hardcode `language: "pt"` in JS; add a dropdown
4. **Conversational tutor LLM** - wire to `llm-core` StructuredLLMChain
5. **Progress tracking** - persist `WordResult` outcomes to user progress store
6. **Session persistence** - replace in-memory `_active_rounds` with Redis/DB for production
7. **API tests** - cover start/submit flows for each exercise type
