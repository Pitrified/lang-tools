@.github/copilot-instructions.md

## Claude Code

This repo's canonical instructions live in `.github/copilot-instructions.md`
(imported above) so Copilot and Claude share one source of truth.

`lang-tools` is the content + data half of the language-learning split: it owns
the lexicon model, its build and store, the content read API, and the
content-producing LLM chains. The learner-facing concerns live in the sibling
`lang-tutor` repo, which depends on `lang-tools`. The dependency is strictly one-way: `lang-tools` must
never import `lang-tutor`.

Planning lives in `scratch_space/`, one numbered folder per initiative, `tracking.md`
first (current: `scratch_space/09_concept_model/tracking.md`).
