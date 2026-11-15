---
name: unranked-review
description: Review one batch of pt words that have no frequency for the lang-tools lexicon, labelling each as common, uncommon, rare, misspelled, not Portuguese or malformed, and apply the labels. Use when asked to review unranked-word batches, or when an orchestrating session hands you an unranked batch id (u0001, u0002, ...).
---

# Unranked-word review: one batch

You label one batch (about 200 pt words) and record the labels. The work is pure judgement: do not
explore the codebase, do not open other files than the ones named here, and keep your final report
to a few lines.

All commands run from the `lang-tools` repo root. `CLI` below stands for:

```bash
SAMPLE_API_KEY=placeholder-not-a-secret uv run --no-sync python -m lang_tools.lexicon.ingestion.unranked_review_cli
```

## Steps

1. **Read the rules** in `docs/guides/unranked_review.md`, once and in full. They define the six
   labels, the hard cases, the reasons and the label format.
2. **Get the batch:** `CLI serve --batch <id>` (the id you were given, for example `u0003`).
   Serving an id that is already reserved prints the same batch again, so it is safe to repeat.
   Each item is a line `n word (part of speech)`, then one indented line per concept the word
   is linked to, `gloss [English members]`.
3. **Label every item** with one of `c`, `u`, `r`, `m`, `f`, `x`. Decide the clear ones quickly;
   spend your thought on valid pt-PT or pt-BR spellings (not `m`), loanwords Portuguese uses
   (real words, bucket them), and forms that might be `m` or `x`. Write a reason after `#` on
   every `m`, `f` and `x`, the correct spelling after `m` and the language code after `f`.
4. **Write the labels** to `data/work/unranked_review/<id>.labels.txt`, one line per item, in the
   label format.
5. **Apply:** `CLI apply --batch <id> --labels data/work/unranked_review/<id>.labels.txt`. If it
   prints `NOT APPLIED`, fix every listed problem in the labels file and run it again. Never edit
   `data/curated/` files by hand.
6. **Report** in at most four lines: the batch id, the count per label, and any problem worth a
   human look. Do not paste the labels.

## Orchestrating several batches

A session that runs many batches keeps its own context small by handing each batch to a subagent:

- Before the first batch: `CLI worklist` writes the worklist from the built corpus (rebuild the
  corpus first when it changed). `CLI status` shows the labelled count, the count per label and
  the pending batches.
- Pick ids in sequence (`u0001`, `u0002`, ...). Start each subagent with a prompt like: "Follow
  `.claude/skills/unranked-review/SKILL.md` in `/home/pmn/repos/lang-tools` for batch `u0003`, then
  report." Run a handful at a time; reservations are locked, so parallel subagents never get the
  same words.
- To label words again after a review of the labels or a rulebook change, serve them as a
  re-check: `CLI recheck --batch r0001 --words word1,word2`, then label and apply it like any
  batch. The new label wins: a word kept again is restored, a word dropped loses its bucket.
- After the batches, run `CLI status`, then commit `data/curated/unranked_review_log.jsonl`,
  `data/curated/commonness_buckets.jsonl`, `data/curated/member_form_drops.jsonl` and the label
  files under `data/work/unranked_review/` (under Git LFS; add them with `git add -f`), and
  rebuild the corpus.
