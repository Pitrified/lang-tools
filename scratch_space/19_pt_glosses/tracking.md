# implementation tracking

Write the 8,877 pt glosses missing since pt moved to OpenWordnet-PT, with Claude subagents over
served batches instead of the paid OpenAI chain.
Analysis and decisions in [`00_start.md`](00_start.md).

## Key decisions

- Subagents, not the OpenAI chain: no API key on this box, and the batch tooling of the
  look-alike and sense reviews already exists (`00_start.md`, Original note).
- 200 items per batch, as the past subagent runs (`00_start.md` Q1).
- The rules are `prompts/gloss_translate/v3.jinja` as is, assessed on the 600-gloss pilot
  (`00_start.md` Q2).
- Provenance in a batch log, rows unchanged; no gold items (`00_start.md` Q3, Q4).
- New rows are appended, never written over the 174k existing ones; the notebook gets the same
  fix (`00_start.md` Q6).
- pt-BR, as the existing pt glosses (`00_start.md` Q7).

## Phases

| # | Phase | Plan | Status |
| - | ----- | ---- | ------ |
| 1 | Tooling | [`01_tooling.md`](01_tooling.md) | planned |
| 2 | Pilot | [`02_pilot.md`](02_pilot.md) | planned |
| 3 | Full run and rebuild | [`03_full_run.md`](03_full_run.md) | draft |

Status values: draft / planned / in progress / done / superseded / discarded.

## Log

Append-only. Newest at the bottom.

- 2026-11-13 : bootstrapped from `open_points.md` after a live OpenAI sample failed for lack of
  a key (nothing spent); the user chose subagents; Q1 to Q7 answered and folded in.
- 2026-11-13 : wrote the sub-plans and reviewed them. Two corrections: serve excludes the keys in
  the batch log, not every key with a curated row (the October run's rejected pt row still needs
  a gloss); wrong glosses are corrected through `gloss_overrides.jsonl`, since the backfill
  applier keeps the first accepted row per concept (a `correct` subcommand, phase 1).
