---
name: meaning-review
description: Review one batch of the lang-tools lexicon's meanings, labelling each pt word of a meaning as keep, a form of another word, or drop (w batches), or picking the first en word of a meaning (l batches), and apply the labels. Use when asked to review meaning or lead batches, or when an orchestrating session hands you a batch id (w0001, l0001, ...).
---

# Meaning review: one batch

You label one batch (about 100 meanings) and record the labels. The work is pure judgement: do
not explore the codebase, do not open other files than the ones named here, and keep your final
report to a few lines.

All commands run from the `lang-tools` repo root. `CLI` below stands for:

```bash
SAMPLE_API_KEY=placeholder-not-a-secret uv run --no-sync python -m lang_tools.lexicon.ingestion.meaning_review_cli
```

## Steps

1. **Read the rules** in `docs/guides/meaning_review.md`, once and in full. They define the labels
   of both kinds of batch, the hard cases, the reasons and the label format.
2. **Get the batch:** `CLI serve --batch <id>` (the id you were given, for example `w0003`).
   Serving an id that is already reserved prints the same batch again, so it is safe to repeat.
   A `w` batch shows meanings with numbered pt words; an `l` batch numbered meanings with their en
   words.
3. **Label every number.** In a `w` batch, `k`, `f <base>` or `d`; in an `l` batch, `k` or
   `l <word>`. Decide the clear ones quickly; spend your thought on the bracketed hints and on
   words that may name something else. Write a reason after `#` on every `d`.
4. **Write the labels** to `data/work/meaning_review/<id>.labels.txt`, one line per number, in the
   label format.
5. **Apply:** `CLI apply --batch <id> --labels data/work/meaning_review/<id>.labels.txt`. If it
   prints `NOT APPLIED`, fix every listed problem in the labels file and run it again. Never edit
   `data/curated/` files by hand.
6. **Report** in at most four lines: the batch id, the count per label, and any problem worth a
   human look. Do not paste the labels.

## Orchestrating several batches

A session that runs many batches keeps its own context small by handing each batch to a subagent:

- Before the first batch: `CLI worklist` writes both worklists from the built corpus (rebuild the
  corpus first when it changed). `CLI status` shows the reviewed count, the count per label and
  the pending batches of each kind.
- Pick ids in sequence (`w0001`, `w0002`, ...; `l0001`, ...). Start each subagent with a prompt
  like: "Follow `.claude/skills/meaning-review/SKILL.md` in `/home/pmn/repos/lang-tools` for batch
  `w0003`, then report." Run a handful at a time; reservations are locked, so parallel subagents
  never get the same meanings.
- After the batches, run `CLI status`, then commit `data/curated/meaning_review_log.jsonl`,
  `data/curated/sense_additions.jsonl`, `data/curated/member_form_drops.jsonl`,
  `data/curated/lead_translations.jsonl` and the label files under `data/work/meaning_review/`
  (under Git LFS; add them with `git add -f`), and rebuild the corpus.
