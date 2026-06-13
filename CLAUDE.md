@.github/copilot-instructions.md

## Claude Code

This repo's canonical instructions live in `.github/copilot-instructions.md`
(imported above) so Copilot and Claude share one source of truth.

`lang-tools` is the content + data half of the language-learning split: it owns
the `Word` model, ingestion, the word store, and the content-producing LLM
chains. The learner-facing concerns live in the sibling `lang-tutor` repo, which
depends on `lang-tools`. The dependency is strictly one-way: `lang-tools` must
never import `lang-tutor`.
