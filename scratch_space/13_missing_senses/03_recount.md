---
status: done
---

# Phase 3 - rebuild and re-count

## Overview

Rebuild with the new rows and measure the result on the same items as phase 2.
Context: [`00_start.md`](00_start.md), "Measurement". Depends on [`02_review.md`](02_review.md).

## Plan

- Rebuild (`docs/guides/rebuild_corpus.md`), run the gate, note the additions applied and stale.
- One more agent review of the same 1,000 cards, same rules, for the after table; it writes no
  curated row unless it finds a new error, which is then labelled and applied as in phase 2.
- Recount the stale look-alike rows (34 on 2026-11-06; the 28 on removed lemmas should mostly
  re-attach).
- Restart the 8010 API on the new corpus.

## Done when

- Gate PASS; the before and after tables sit side by side here; each card still wrong has its
  reason.

## What the implementation found
Rebuilds: three, the last with `m0007` and the notes drops. Final build: `sense_additions` 197
senses added, 63 lemmas created, 0 stale; best senses 300 applied, 0 stale; look-alikes 6,838
applied, 10 stale (34 before the phase: the rows on removed lemmas re-attached); gate PASS.
pt gloss coverage 99.9%: 33 concepts first linked to pt by an addition carry no pt gloss,
open for a paid gloss-translate run.

Before and after, the pt top 1,000:

| | Before | After |
| --- | --: | --: |
| corpus | before any review of this folder | rebuilt with `m0001` to `m0006` |
| rulebook | `292dd6cd73a5` | `35151d6c864c` |
| reviewer changes | 157 (first review) | 124 (second review, blind) |
| of which a defect of the tool | | 74 put back a pin a re-check `k` had released |
| cards a reviewer would change | 157 (15.7%) | 50 (5.0%) |
| first-review changes kept | | 154/157 (98%) |
| gold | 8/10 | 10/10 |

The pin defect (a label that did not pin wrote a row with no concept, so a re-check `k`
released an earlier pin) is fixed in `_item_rows`, with a test, and the 97 released pins were
restored by correction rows before `m0007`. `m0007` re-labelled the 62 items still in question
under the same rules (the 50 changes and the 12 released-pin words the after review kept on
the frequency card): 33 kept, 4 pinned, 25 added; gold 2/2. Those 29 changes carry one review
each.

Cards still wrong, with their reasons (from the reviewers' reports):

- No concept to link: *deve*, *possa* (WordNet holds no modal verbs; they stay out), *quão*
  ("how"), *eis* ("here is"; the card is "here"), *quarta* "Wednesday" (only *quarta-feira*
  holds it), *pena* "penalty, sentence" and *claro* "clear" (not linked to pt).
- Frequency from a name: *lula*, *vice*, *oliveira*, kept on their real common senses.
- Frequent form not linked: *liga* (the verb *ligar*), *meio* ("half" or "middle" over sense 1),
  *porra* (the expletive).
- The pt number words absent from the corpus altogether (*doze*, *quinze*, *trinta*), found in
  phase 2, out of this folder's scope.
