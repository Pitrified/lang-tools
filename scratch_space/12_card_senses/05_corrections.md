---
status: planned
---

# Phase 5 - corrections

## Overview

Make a reviewed drop retractable, and correct the few pt review results the re-list flagged.
Context: [`00_start.md`](00_start.md) Q7, Q9, Q10; the findings in
[`04_review_run.md`](04_review_run.md).

## Plan

- **Latest row wins on the drop file:** `apply_form_drops` keys the accepted rows on
  (`lemma_id`, `concept_key`) and keeps the last one per key, so a later `drop: false` row
  retracts an earlier drop. The committed file holds no repeated key today (273 rows), so the
  build is unchanged until a retraction is written. The closed-class drops, passed in by the
  pipeline, have no repeats either.
- **Two commands** (Q10, a), keyed on word and language, both `model="human"` with a reason:
  - `sense_review_cli restore` writes a `drop: false` row for each of the lemma's dropped
    senses, or only the keys given;
  - `sense_review_cli pin` writes a new `BestSense` row for a sense key;
    `best_senses.jsonl` is already latest-row-wins.
- **Apply** (Q9, a): restore *moderna* "contemporaneous" (`93abec283edc`), re-pin *copa* to
  "a drinking glass". Rebuild, run the gate, check both cards on the read API.
- Tests: a retraction restores a sense and its lemma; a repin moves the card.
- Docs: the "cannot be retracted yet" paragraph in `docs/library/lexicon.md`, and the two
  commands in the skill's orchestration notes. The rulebook stays as it is: corrections are a
  human step, not a batch label, so its hash does not move.

## Out of scope

- Adding the missing senses (*sede*, *sentido*, *natal*, *vinte* "twenty", ...):
  `13_missing_senses` (`00_start.md` Q8). The other eight lost lemmas come back through it.
- es and fr (Q6).

## Done when

- A later row retracts a drop, tested; `make check` passes and the docs build.
- The chosen corrections are applied and committed, the rebuild passes the gate, and the read
  API shows them.
