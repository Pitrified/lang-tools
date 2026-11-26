---
status: done
---

# Phase 3 - Pilot

## Overview

One batch, `p0001`, with the gold pairs first, to test the rulebook before the rest.
Context: [`00_start.md`](00_start.md) (Q4, Q5); depends on [`02_harness.md`](02_harness.md).

## Plan

- A subagent follows the skill for `p0001` on Sonnet at high effort (Q5).
- `CLI gold`; then I read the 50 other labels against the rulebook, and the overlap with
  acerta's read verdicts (`shared` against `s`, `good` against `d`).
- A rulebook change, if the read calls for one, is made before phase 4 and the pilot re-checked.

## Done when

- Gold agreement and my read logged in `tracking.md`.
- Below 45 of the 50 gold pairs, or a read that finds the rulebook unclear, the loop stops and
  asks before phase 4: Q5 settled the model, so a change to it is the user's.

## What the implementation found

- `p0001` (100 pairs, gold first), Sonnet at high effort, about 81k tokens and 71 s:
  39 `s`, 58 `d`, 3 `w`, 15 edge cases. Gold 49/50; the miss, pt *geladeira* / it *gelateria*
  (`w` -> `d`), is defensible: "milk bar" is near enough an ice-cream shop.
- My read of the 50 others: none wrong; three debatable (*falta* / en *fault* `s` via
  *cometer uma falta*, *vinha* / en *vine* `d!`, *carro* / it *carro* `s` via *carro de boi*).
  The `w` labels are right (it *terza*, *quinta*, *sesta* shown with a rare sense).
- Against acerta's read on the 69 pairs it covers: its `shared` is `s` 13 times and `d` 2;
  its `good` is `d` 37 times and `s` 10, mostly shared meanings it missed (*logo*, *sol*).
- No rulebook change; phase 4 runs as planned.
