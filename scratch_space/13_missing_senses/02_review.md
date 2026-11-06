---
status: done
---

# Phase 2 - agent review

## Overview

One agent review of the pt top 1,000 cards and the 60 removed lemmas, a measured second review
of 500 targeted items (Q8), then apply. The labels are also the before table.
Context: [`00_start.md`](00_start.md), "Measurement", Q2 note, Q8. Depends on
[`01_tooling.md`](01_tooling.md).

## Plan

- Worklist: the 1,000 cards `12_card_senses` reviewed (same ids, so the counts compare); the 60
  lemmas that review removed are among them, served from their dropped links. Batches of 200
  (`m0001` to `m0005`), one subagent per batch.
- Gold for the new action (from phase 1): four unambiguous words just below the top 1,000 whose
  everyday meaning is not linked (*funcionário* "employee", *gatos* "cats", *turma* "class",
  *carreira* "career"), added to the gold file and recorded with `import-gold`, which now writes
  the addition a gold answer needs.
- The four gold verb forms (*homens*, *seja*, *tinha*, *olha*) had "no right card" as their
  answer, which Q1 a changes: their gold now names the base word's concept, and the corpus got
  the same fix through `add` with a form note. The gold file is now latest-row-wins per lemma,
  so the old answers stay as history.
- Measure the cost on the first batch and report it before the rest.
- First review `m0001` to `m0005`. Tally the causes from the labels and their reasons, not from
  a list fixed up front.
- Second review, blind, on 500 targeted items: every item the first review changes, filled with
  kept items. `agreement` over the two; at 90% or more on the changes, the first review's labels
  stand; below, the disagreements point at the rule to fix, which is fixed and the affected items
  served again.
- Write the measurement up as a repeatable method in `docs/guides/missing_senses.md` (the first
  meta-experiment on the review method, Q8), with what it found and what to try next.
- Apply; commit the curated files and the log.
- The second review came in at 69% on the changed items (`00_start.md` Q10): the rules were
  fixed (near misses, Q9's frequent reading, the twin tie-break, drops alongside an addition),
  `concepts` shows commonness, `agreement` counts twins apart, and the 53 disagreements are
  served again as `m0006` under the new rulebook. Phase 3's second review measures the fix.

## Out of scope

- es and fr (Q5).

## Done when

- Every item has an applied label; the before table (per action and cause), the same-rules
  agreement and the gold agreement are written here.

## What the implementation found

The worklist is 1,000 items, not 1,064: the 60 removed lemmas were already among the 1,000
(`worklist-removed` adds none, and now skips gold lemmas).

Before table, first review `m0001` to `m0005` (rulebook `292dd6cd73a5`), 1,000 items:

| Outcome | Items | Cause, from the reasons |
| --- | --: | --- |
| kept | 843 | |
| added | 147 | 94 an inflected form linked to its base word with a form note (*vão*, *veio*, *regras*); 53 an everyday meaning not linked (*sede* "headquarters", *obrigado* "thanks", *sexta* "Friday") |
| pinned | 5 | the right sense was listed lower |
| senses dropped | 17 | a wrong link, mostly a near miss left after an addition |
| lemma dropped | 1 | |
| edge cases | 32 | |

38 of the 60 removed lemmas came back with an addition; the rest stay out as names, English
words, or with no concept to link (*deve*, *dentre*: WordNet holds no modal verbs). Gold
8/10, both misses on the gold side (*turma* widened; *era*, Q9). The notes files gave 18 wrong
members, 17 dropped by hand.

Same-rules agreement, second review `n0001` to `n0003` on 500 targeted items (the 157 changed
and 343 kept cards with two or more senses): 458 same card (92%), 447 same outcome, 108/157 on
the changed items (69%, below the 90% bar), 117/157 counting the 9 WordNet twins. The 53
disagreements: 28 the threshold for a near miss, 14 a different concept for the same meaning
(9 of them twins by the tool's test), 11 an extra drop. Gold 5/6 (the miss is *era*).
Second-review cost: about 290k subagent tokens; the first review took about 5% of the 5-hour
meter a batch.

Fixes (Q9, Q10): the rulebook rules for near misses, the frequent reading, twins and drops
alongside an addition (`35151d6c864c`); `m0006` re-labelled the 53 under them (4 kept, 2
pinned, 7 senses dropped, 43 added; gold 2/2). The rulebook examples come from those items, so
`m0006` measures nothing; phase 3's second review does. Q11: a re-check is served from the
worklist snapshot, so it cannot see or undo an earlier review's rows; fixed in phase 3 before
its second review.
