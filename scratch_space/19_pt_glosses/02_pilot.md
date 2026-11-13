---
status: planned
---

# Phase 2 - Pilot

## Overview

Three batches (600 glosses), each written by one subagent, all read by the orchestrating
session before more is served: the assessment of the v3 rules for this path (`00_start.md` Q2).
Context: [`00_start.md`](00_start.md), depends on [`01_tooling.md`](01_tooling.md).

## Goals

1. Measure how many of 600 glosses are wrong, and how (meaning, register, added facts, pt-BR,
   format), against the English gloss and the member words.
2. Decide whether the rules hold as they are.

## Plan

- Serve and run `g0001` to `g0003`, three subagents in parallel, by the skill.
- Read all 600, and write `02.1_pilot_assessment.md`: counts per verdict and per failure kind,
  every wrong gloss with a corrected one, and a recommendation on the rules.
- Correct each wrong gloss with `CLI correct`, an accepted row in `gloss_overrides.jsonl`.
  A second backfill row for the same key would not work: `apply_gloss_backfill` fills from the
  first accepted row and skips the later ones as "a gloss exists"; the overrides are applied
  before the backfill and always win.
- Report to the user; the next phase starts on their go.

## Out of scope

- Serving past `g0003`.

## Done when

- `02.1_pilot_assessment.md` is written and the user has read it.

## What the implementation found
