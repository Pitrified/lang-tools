---
name: false-friend-meaning-review
description: Review one batch of en and it words that are false friends of pt words for the lang-tools lexicon, picking the sense each word mainly means (keep sense 1, pin another, or say the main meaning is missing), and apply the labels. Use when asked to review false-friend meaning batches, or when an orchestrating session hands you a batch id (f0001, f0002, ...).
---

# False-friend meaning review: one batch

You label one batch (about 100 en and it words) and record the labels. The work is pure
judgement: do not explore the codebase, do not open other files than the ones named here, and keep
your final report to a few lines.

All commands run from the `lang-tools` repo root. `CLI` below stands for:

```bash
SAMPLE_API_KEY=placeholder-not-a-secret uv run --no-sync python -m lang_tools.lexicon.ingestion.false_friend_meaning_review_cli
```

## Steps

1. **Read the rules** in `docs/guides/false_friend_meaning_review.md`, once and in full. They
   define the question, the three labels, the hard cases and the label format.
2. **Get the batch:** `CLI serve --batch <id>` (the id you were given, for example `f0003`).
   Serving an id that is already reserved prints the same batch again, so it is safe to repeat.
   Each item is a line `n language word (part of speech)`, then one indented line per pt word it
   is a false friend of, then one numbered line per sense, `K gloss [pt: ... | en: ... | it: ...]`.
3. **Label every item** with `k`, `pK` or `m`. Decide the clear ones quickly; spend your thought
   on words with many senses, a noun and a verb, or near senses. Add `!` after a judgement call,
   and a reason after `#` on every `m`.
4. **Write the labels** to `data/work/false_friend_meaning_review/<id>.labels.txt`, one line per
   item, in the label format.
5. **Apply:** `CLI apply --batch <id> --labels data/work/false_friend_meaning_review/<id>.labels.txt`.
   If it prints `NOT APPLIED`, fix every listed problem in the labels file and run it again. Never
   edit `data/curated/` files by hand.
6. **Report** in at most four lines: the batch id, the count per label and of edge cases, and any
   problem worth a human look. Do not paste the labels.

## Orchestrating several batches

A session that runs many batches keeps its own context small by handing each batch to a subagent:

- Before the first batch: `CLI worklist` writes the worklist from the built corpus, the gold words
  first (rebuild the corpus first when it changed). `CLI status` shows the labelled count, the
  count per label and the pending batches; `CLI gold` the agreement with the gold set.
- Pick ids in sequence (`f0001`, `f0002`, ...). Start each subagent with a prompt like: "Follow
  `.claude/skills/false-friend-meaning-review/SKILL.md` in `/home/pmn/repos/lang-tools` for batch
  `f0003`, then report." Run a handful at a time; reservations are locked, so parallel subagents
  never get the same words.
- To label words again after a review of the labels or a rulebook change, serve them as a
  re-check: `CLI recheck --batch f9001 --words it:dito,en:font` (language and text, since en and
  it share spellings), then label and apply it like any batch. The new label wins.
- After the batches, run `CLI status`, then commit `data/curated/best_senses.jsonl`,
  `data/curated/false_friend_meaning_log.jsonl` and the label files under
  `data/work/false_friend_meaning_review/` (under Git LFS; add them with `git add -f`), and
  rebuild the corpus.
