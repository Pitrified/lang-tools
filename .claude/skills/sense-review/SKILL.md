---
name: sense-review
description: Review one batch of the most frequent drill cards (pt first) for the lang-tools lexicon, keeping each card, pinning the right sense, or dropping the concept links the word never means, and apply the labels. Use when asked to review card-sense batches, or when an orchestrating session hands you a sense batch id (s0001, ...).
---

# Card-sense review: one batch

You label one batch (about 200 words) of drill cards and record the labels. The work is pure
judgement: do not explore the codebase, do not open other files than the ones named here, and keep
your final report to a few lines.

All commands run from the `lang-tools` repo root. `CLI` below stands for:

```bash
SAMPLE_API_KEY=placeholder-not-a-secret uv run --no-sync python -m lang_tools.lexicon.ingestion.sense_review_cli
```

## Steps

1. **Read the rules** in `docs/guides/sense_review.md`, once and in full. They define the labels,
   the hard cases, the reasons, edge cases and the label format.
2. **Get the batch:** `CLI serve --batch <id>` (the id you were given, for example `s0003`).
   Serving an id that is already reserved prints the same batch again, so it is safe to repeat.
   Each item is a line `n language word (part of speech)`, then one indented line per sense,
   `k gloss [translations]`. Sense 1 is the card's meaning today.
3. **Label every item.** Most cards are right (`k`); decide those quickly. Spend your thought on
   words that are also a frequent verb form or plural, and on words whose sense 1 is a rare
   reading. Write a reason on every `d` and `x`. Mark genuine judgement calls with `!`.
4. **Write the labels** to `data/work/sense_review/<id>.labels.txt`, one line per item, in the
   label format.
5. **Apply:** `CLI apply --batch <id> --labels data/work/sense_review/<id>.labels.txt`. If it
   prints `NOT APPLIED`, fix every listed problem in the labels file and run it again. Never edit
   `data/curated/` files by hand.
6. **Report** in at most four lines: the batch id, the counts (kept, pinned, dropped senses,
   dropped lemmas), the gold agreement (`gold_agree` out of `gold_keys`), the number of edge
   cases, and any problem worth a human look. Do not paste the labels.

## Orchestrating several batches

A session that runs many batches keeps its own context small by handing each batch to a subagent:

- Before the first batch: `CLI worklist --language pt` writes the worklist, and `CLI import-gold`
  records the gold lemmas as reviewed. `CLI status` shows the progress per language, the pending
  batches and the gold agreement so far.
- Pick ids in sequence (`s0001`, `s0002`, ...). Start each subagent with a prompt like: "Follow
  `.claude/skills/sense-review/SKILL.md` in `/home/pmn/repos/lang-tools` for batch `s0003`, then
  report." Run a handful at a time; reservations are locked, so parallel subagents never get the
  same words.
- After the batches, run `CLI status`, look at the gold misses in
  `data/curated/sense_review_log.jsonl`, then commit `data/curated/best_senses.jsonl`,
  `data/curated/member_form_drops.jsonl`, the log and the label files under
  `data/work/sense_review/` (under Git LFS; add them with `git add -f`), and rebuild the corpus.
- A wrong verdict found later is corrected by hand, never by a subagent and never by editing the
  files: `CLI restore --language pt --word <w> --reason "<why>"` retracts the word's drops
  (`--keys` to name some), `CLI pin --language pt --word <w> --key <concept key>` pins another
  sense. Both write a later row; the latest row wins.
