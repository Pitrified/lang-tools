---
name: lookalike-review
description: Review one batch of look-alike word pairs (pt vs en/it) for the lang-tools lexicon, labelling each as cognate, partial or full false friend, or unrelated, and apply the labels. Use when asked to review look-alike / false-friend batches, or when an orchestrating session hands you a batch id.
---

# Look-alike review: one batch

You label one batch (100 or 200 items) of Portuguese / English-or-Italian look-alike pairs and record the
labels. The work is pure judgement: do not explore the codebase, do not open other files than the
ones named here, and keep your final report to a few lines.

All commands run from the `lang-tools` repo root. `CLI` below stands for:

```bash
SAMPLE_API_KEY=placeholder-not-a-secret uv run python -m lang_tools.lexicon.ingestion.lookalike_review_cli
```

## Steps

1. **Read the rules** in `docs/guides/lookalike_review.md`, once and in full. They define the four
   kinds, the hard cases, the note format, edge cases and the label format.
2. **Get the batch:** `CLI serve --batch <id>` (the id you were given, for example `a0003`).
   Serving an id that is already reserved prints the same batch again, so it is safe to repeat. Each
   line is `n language | pt word [pt senses] | known word [known senses]`.
3. **Label every item.** Go line by line, apply the rules, and decide quickly on the clear cases
   (most are plain cognates or plain coincidences). Spend your thought on the near-identical pairs and
   the ones whose meanings partly overlap. Write a note on every `f` and `p`. Mark genuine judgement
   calls with `!`.
4. **Write the labels** to `data/work/lookalike_review/<id>.labels.txt`, one line per item, in the
   label format.
5. **Apply:** `CLI apply --batch <id> --labels data/work/lookalike_review/<id>.labels.txt`. If it
   prints `NOT APPLIED`, fix every listed problem in the labels file and run it again. Never edit
   `data/curated/` files by hand.
6. **Report** in at most four lines: the batch id, the kinds count, the gold agreement (`gold_agree`
   out of `gold_keys`), the number of edge cases, and any problem worth a human look. Do not paste the
   labels.

## Orchestrating several batches

A session that runs many batches keeps its own context small by handing each batch to a subagent:

- Pick ids by tier and sequence (`a0001`, `a0002`, ... for tier A). `CLI status` shows the progress
  per tier, the pending batches and the gold agreement so far.
- Start each subagent with a prompt like: "Follow `.claude/skills/lookalike-review/SKILL.md` in
  `/home/user/lang-tools` for batch `a0003`, then report." Run a handful at a time; reservations are
  locked, so parallel subagents never get the same items.
- After the batches, run `CLI status`, look at the gold misses in
  `data/curated/lookalike_review_log.jsonl`, then commit `data/curated/lookalikes.jsonl` and the log
  (both under Git LFS; add them with `git add -f`).

## Re-checking pairs after a rule change

When the guide changes, older rows keep their old `prompt_sha`. To re-check a chosen set of them,
write their keys (`{target_id}:{known_id}`, one per line) to a file and serve them with
`CLI recheck --batch r0001 --keys keys.txt --size 200`, then label and apply as usual. `recheck`
skips keys that are pending or already have a row under the current guide, so successive ids
(`r0001`, `r0002`, ...) walk through the list. The new rows are appended; the corpus build keeps
the later row of a pair. A subagent handed an `r` id follows the steps above, with the batch
already served.
