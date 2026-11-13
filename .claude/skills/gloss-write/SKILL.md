---
name: gloss-write
description: Write one batch of missing Portuguese (pt-BR) dictionary glosses for the lang-tools lexicon, from each concept's English gloss, and apply them. Use when asked to write pt gloss batches, or when an orchestrating session hands you a gloss batch id (g0001, g0002, ...).
---

# Gloss writing: one batch

You write one batch (200 items) of Portuguese glosses for concepts that have Portuguese words but
no Portuguese gloss, and record them. The work is pure writing: do not explore the codebase, do
not open other files than the ones named here, and keep your final report to a few lines.

All commands run from the `lang-tools` repo root. `CLI` below stands for:

```bash
SAMPLE_API_KEY=placeholder-not-a-secret uv run --no-sync python -m lang_tools.lexicon.ingestion.gloss_write_cli
```

## Steps

1. **Read the rules** in `src/lang_tools/prompts/gloss_translate/v3.jinja`, once and in full.
   It is the prompt the paid backfill used; read it as written for you, with
   `{{ language_name }}` = Portuguese and `{{ variety }}` = Brazilian Portuguese (pt-BR spelling
   and vocabulary). Ignore its last part about the `glosses` output; the format is below.
2. **Get the batch:** `CLI serve --batch <id>` (the id you were given, for example `g0003`).
   Serving an id that is already reserved prints the same batch again, so it is safe to repeat.
   Each line is `n | English gloss | English words | Portuguese words`.
3. **Write every gloss.** Render the English gloss in natural Portuguese, in the register of a
   monolingual dictionary, saying what the English says and only that. The words are context:
   they tell you which sense is meant. Most items are quick; spend your thought on the ones whose
   English gloss is ambiguous or technical.
4. **Write the file** `data/work/gloss_write/<id>.txt`: one line per item, the item number, a
   tab, the gloss. No headword, no quotes, no trailing notes.
5. **Apply:** `CLI apply --batch <id> --glosses data/work/gloss_write/<id>.txt`. If it prints
   `NOT APPLIED`, fix every listed problem in the file and run it again. The screen refuses a
   missing or doubled number, a gloss that only repeats a Portuguese word, an untranslated one,
   and a runaway length. Never edit `data/curated/` files by hand.
6. **Report** in a few lines: the batch id, the count applied, and two lists by item number,
   each with the English words and a phrase:
   - `broken English:` every item whose English gloss looks truncated, is a fragment, or carries
     a stray example (write the best gloss you can; the orchestrator corrects these);
   - `wrong pt words:` every item whose Portuguese words do not mean the concept (gloss it from
     the English anyway).
   Write `none` for an empty list. Do not paste the glosses.

## Orchestrating several batches

A session that runs many batches keeps its own context small by handing each batch to a subagent:

- Pick ids in sequence (`g0001`, `g0002`, ...). `CLI status` shows the glosses left, the ones
  written and the pending batches.
- Start each subagent with a prompt like: "Follow `.claude/skills/gloss-write/SKILL.md` in
  `/home/pmn/repos/lang-tools` for batch `g0003`, then report." Run a handful at a time;
  reservations are locked, so parallel subagents never get the same items.
- After a round, run `CLI status`, then commit `data/curated/gloss_backfill.jsonl` and
  `data/curated/gloss_write_log.jsonl` (both under Git LFS; add them with `git add -f`).
- The rows are written as `proposed`. They are accepted after a sampled review with
  `gloss_backfill.accept_run(..., languages=["pt"])`, and reach the corpus at the next rebuild.
- A wrong gloss found on review is corrected with `CLI correct --key pt:<concept_key> --gloss
  "..."`, which writes an accepted gloss override; the build applies overrides first.
