---
status: planned
---

# Phase 1 - Rulebook and harness

## Overview

The agents need a rulebook, a worklist and the serve / apply commands the sense review has.
Context: [`00_start.md`](00_start.md).

## Plan

- `docs/guides/unranked_review.md`: the labels, with examples from the sample:
  `c` common (a learner meets it: peúga, pigarrear), `u` uncommon (real, educated register:
  psicanalisar), `r` rare (specialist or archaic: conquiliologia, joeirar), `m` misspelled
  (with the right spelling: magestoso -> majestoso), `f` not Portuguese (with the language:
  walkout en), `x` malformed (canodachaminé). A reason on `m`, `f`, `x`. Its hash is
  stored on every row.
- `ingestion.unranked_review` and `unranked_review_cli`: `worklist` (the single lowercase
  pt lemmas with no frequency, each with its glosses and English members), `serve --batch`
  through `review_batches`, `apply` that validates every line and writes rows, `status`.
- Curated output: `data/curated/unranked_review_log.jsonl` (every label), drop rows
  appended to `member_form_drops.jsonl` (one per concept link, reason and rulebook hash),
  bucket rows to `data/curated/commonness_buckets.jsonl`; latest row wins per lemma.
- `.claude/skills/unranked-review/SKILL.md`, the one-batch procedure, like sense-review.
- Tests on the seed: worklist selection, label parsing and its errors, apply writing the
  three kinds of row, a re-label winning.

## Done when

- `make check` passes; a batch can be served and applied by hand.
