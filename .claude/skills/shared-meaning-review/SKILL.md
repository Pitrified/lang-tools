---
name: shared-meaning-review
description: Review one batch of false-friend pairs (a pt word and an en or it look-alike) for the lang-tools lexicon, labelling whether Portuguese speakers use the pt word for the look-alike's main meaning (shared, distinct, or the main meaning shown is wrong), and apply the labels. Use when asked to review shared-meaning batches, or when an orchestrating session hands you a batch id (p0001, p0002, ...).
---

# Shared-meaning review: one batch

You label one batch (about 100 pt and en or it pairs) and record the labels. The work is pure
judgement: do not explore the codebase, do not open other files than the ones named here, and keep
your final report to a few lines.

All commands run from the `lang-tools` repo root. `CLI` below stands for:

```bash
SAMPLE_API_KEY=placeholder-not-a-secret uv run --no-sync python -m lang_tools.lexicon.ingestion.shared_meaning_review_cli
```

## Steps

1. **Read the rules** in `docs/guides/shared_meaning_review.md`, once and in full. They
   define the question, the three labels, the hard cases and the label format.
2. **Get the batch:** `CLI serve --batch <id>` (the id you were given, for example `p0003`).
   Serving an id that is already reserved prints the same batch again, so it is safe to repeat.
   Each item is a line `n pt word (part of speech) ~ language look-alike (kind)`, then the
   edge's note, then the pt word's senses (`K gloss [en: ... | it: ...]`, the first is what the pt
   card shows), then the look-alike's main meaning (`gloss [pt: ... | en: ... | it: ...]`).
3. **Label every item** with `s`, `d` or `w`. Decide the clear ones quickly; spend your thought on
   pt words with a use the sense lines do not show, on technical or regional uses, and on a
   main meaning that looks off. Add `!` after a judgement call, and a reason after `#` on every
   `w`.
4. **Write the labels** to `data/work/shared_meaning_review/<id>.labels.txt`, one line per
   item, in the label format.
5. **Apply:** `CLI apply --batch <id> --labels data/work/shared_meaning_review/<id>.labels.txt`.
   If it prints `NOT APPLIED`, fix every listed problem in the labels file and run it again. Never
   edit `data/curated/` files by hand.
6. **Report** in at most four lines: the batch id, the count per label and of edge cases, and any
   problem worth a human look. Do not paste the labels.

## Orchestrating several batches

A session that runs many batches keeps its own context small by handing each batch to a subagent:

- Before the first batch: `CLI worklist` writes the worklist from the built corpus, the gold pairs
  first (rebuild the corpus first when it changed). `CLI status` shows the labelled count, the
  count per label and the pending batches; `CLI gold` the agreement with the gold set.
- Pick ids in sequence (`p0001`, `p0002`, ...). Start each subagent with a prompt like: "Follow
  `.claude/skills/shared-meaning-review/SKILL.md` in `/home/pmn/repos/lang-tools` for batch
  `p0003`, then report." Run a handful at a time; reservations are locked, so parallel subagents
  never get the same pairs.
- To label pairs again after a review of the labels or a rulebook change, serve them as a
  re-check: `CLI recheck --batch p9001 --words tarde:it:tardi,próprio:en:proper` (each pair as
  `pt_text:language:known_text`), then label and apply it like any batch. The new label wins.
- After the batches, run `CLI status`, then commit `data/curated/shared_meaning_log.jsonl` and the
  label files under `data/work/shared_meaning_review/` (under Git LFS; add them with
  `git add -f`), and rebuild the corpus.
