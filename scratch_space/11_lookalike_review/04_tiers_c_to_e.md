---
status: planned
---

# Phase 4 - tiers C to E

## Overview

Review tiers C and D, filtered to the pairs whose known word has a Zipf frequency of 3.3 or
more, as phase 3 decided ([`03_tier_depth.md`](03_tier_depth.md), `00_start.md` Q8). The build
drops any trap on a rarer known word, so the filter loses no trap that would reach the corpus;
it skips only cognates on words a learner does not know. Tier E is not reviewed. Context:
[`00_start.md`](00_start.md).

## Plan

- First, one `r` batch for the terse trap notes (lang-tutor's `03_ui_followups/00_start.md` Q9,
  answered b on 2026-11-03): 139 of the 755 served full and partial traps have a note in the old
  terse style (`pt: pull`) that does not say what the tapped word means. The current rulebook's
  Notes section already asks for both sides, and those rows predate it, so `recheck` serves them
  with no guide change. Mine the keys into `data/work/lookalike_review/recheck_notes.txt`
  (latest row `f` or `p` whose note does not start with `pt "`), serve them as `r0011`, apply,
  and rebuild with the first C round.
- Write the key lists `data/work/lookalike_review/filtered_tier_c.txt` and `filtered_tier_d.txt`:
  every pair of the tier with known Zipf 3.3 or more and no reviewed row yet, in worklist
  order (most common pt word first), so an early stop keeps the most useful part.
  About 7,650 (C) and 7,260 (D) pairs, about 39 and 37 batches.
- Serve them with `recheck` as `c0006` onward and `d0006` onward, 200 pairs a batch, ids
  reserved up front, one subagent per id, one commit per round.
- Rounds sized to the 5-hour window, at about 3 session points per agent
  ([`00.1_usage_log.md`](00.1_usage_log.md)); C first, then D.
- Rebuild the corpus after each round and note the edge counts here.

## Out of scope

- Tier E, and the pairs of C and D whose known word is under Zipf 3.3.
- The cheap-model verifier.

## Done when

- Every pair on the two filtered lists has a reviewed row.
- The corpus is rebuilt and the gate passes.
