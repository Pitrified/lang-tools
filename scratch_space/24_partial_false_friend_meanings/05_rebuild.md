---
status: done
---

# Phase 5 - Rebuild and release

## Overview

Rebuild the corpus with the labels, measure the flag against acerta's read, and release.
Context: [`00_start.md`](00_start.md) (Q6); depends on [`04_full_run.md`](04_full_run.md).

## Plan

- Rebuild per `docs/guides/rebuild_corpus.md`; the quality gate passes; the seed restored.
- Measure: flagged pairs per language; against acerta's 274 read partial decoys, how many of the
  104 shared are flagged and how many of the 170 good are; the `w` pairs; the full pairs
  labelled `s`, listed as candidates for a look-alike re-check.
- 0.12.0: the version, the changelog, the frozen API line (Q6).
  The tag `v0.12.0` goes on the merge commit on `main`, as `v0.11.0` did, when the user asks for
  the merge; the merge stays their decision.

## Done when

- `make check` passes on the rebuilt corpus; the measurement logged in `tracking.md`.
- The folder closed: `00_start.md` at `done`, priority 0.

## What the implementation found

- Rebuilt headless (`02_transform.ipynb`, output to the scratchpad), about 4 minutes. Corpus
  counts unchanged; `shared_meanings` flagged 293, stale 0; look-alikes and best senses as
  before (10,310 applied, 113 stale; 1,139 pins). No cognate flagged.
- Flagged by kind and look-alike language: partial 146 en, 123 it; full 14 en, 10 it.
- Against acerta's read: of its 104 partial "shared" decoys, 84 flagged; of its 170 partial
  "good", 65 flagged (mostly shared meanings its decoy read missed, as the pilot showed);
  of its 345 full "good", 14 flagged; of its 41 "bad", 3 flagged.
- The 15 `w` pairs, for a later fix of the look-alike's best sense: pt *terça* ~ it *terza*,
  *quinta* ~ *quinta*, *sexta* ~ *sesta*, *trato* ~ *tratto*, *mesa* ~ *mensa*, *sigilo* ~
  *sigillo*, *persa* ~ *persa*, *poste* ~ en *post*, *posto* ~ en *post*, *prestação* ~
  *prestazione*, *redação* ~ *redazione*, *indireta* ~ *indiretto*, *controlador* ~
  *controllore*, *tremendo* ~ *tremendo*, *matrícula* ~ *matricola*.
- The 24 full pairs labelled `s`, candidates for a look-alike re-check: pt *sorte* ~ en *sort*,
  *falta* ~ *fault*, *largo* ~ *large*, *emergência* ~ *emergence*, *cola* ~ *cola*,
  *confiança* ~ it *confidenza*, *pasta* ~ en *pasta*, *divertido* ~ *diverted*, *craque* ~
  it *crack*, *rumor* ~ it *rumore*, *ginásio* ~ it *ginnasio*, *moda* ~ en *mode*, *alto* ~
  en *alto*, *elenco* ~ it *elenco*, *cartão* ~ it *cartone*, *cômoda* ~ it *comodo*, *afecto*
  ~ en *affect*, *tormenta* ~ en *torment*, *singelo* ~ it *singolo*, *outdoor* ~ en *outdoor*
  and *outdoors*, *manta* ~ it *manto*, *taco* ~ it *tacco*, *reclamar* ~ en *reclaim*.
- Spot check on the built store: pt *tarde*'s it *tardi* (`late`) flagged; pt *bravo* keeps it
  *bravo* (`good`) unflagged, en *brave* and en *bravo* flagged.
- The headless build rewrote the seed's `lookalikes.jsonl` and `senses.jsonl` (the new column);
  restored to HEAD, as in folder 23. The quality report changed only its timestamp; reverted.
  Invariants PASS.
- 0.12.0: version, lock, changelog. The tag `v0.12.0` goes on the merge commit when the user
  merges.
