# implementation tracking

Settle the license of the dataset and of the code, credit every source, and write the dataset
card. Analysis and decisions in [`00_start.md`](00_start.md).

## Key decisions

- pt comes from upstream own-pt (CC BY 4.0), words and links only; our pt glosses stay
  (`00_start.md` Q1).
- fr stays in the local build and out of the shipped dataset until fala is decent in pt
  (`00_start.md` Q2, Q8).
- The wordfreq-derived numbers are facts, credited to wordfreq and its sources (`00_start.md` Q3).
- The dataset is CC BY 4.0, free and open; the code is MIT (`00_start.md` Q4, Q9, Q7).
- The pt switch lands first: share-alike rows cannot be relicensed CC BY (`00_start.md` Q1).
- What is shipped, and how, is `17_distribution`'s; this folder writes the licenses it ships with.

## Phases

| # | Phase | Plan | Status |
| - | ----- | ---- | ------ |
| 1 | pt from own-pt | [`01_own_pt.md`](01_own_pt.md) | done |
| 2 | License files and dataset card | [`02_license_files.md`](02_license_files.md) | in progress |

Status values: draft / planned / in progress / done / superseded / discarded.

## Log

Append-only. Newest at the bottom.

- 2026-11-12 : folder opened from `09_concept_model` phase 10; source licenses verified on the
  web and in the `wn` metadata (wordfreq data is CC BY-SA 4.0; own-pt is CC BY 4.0 and in the
  `wn` index); Q1 to Q6 raised.
- 2026-11-12 : own-pt 1.0.0 compared with omw-pt 1.4 in the scratchpad: same ILIs, similar
  coverage of frequent words, own-pt definitions partly copied from Wikipedia; recorded in
  `00_start.md`.
- 2026-11-12 : Q1 to Q6 answered (own-pt, fr out of the shipped dataset, wordfreq as facts,
  CC BY 4.0, card in a root file and a docs page); code license assessed against reuse in fala.
- 2026-11-13 : Q7 (MIT), Q8 (fr stays out until fala is decent in pt) and Q9 (CC BY 4.0,
  anyone may sell) answered; phases 1 and 2 drafted.
- 2026-11-13 : phase 1 started; review before code: own-pt states its own relations (hypernyms,
  meronyms, 517 pt antonyms) where omw-pt states none, and the reader takes them as is; own-pt
  needs its own version pin. Both written into the plan.
- 2026-11-13 : phase 1 trial build in a scratch folder: own-pt 1.0.0 states hypernym and hyponym
  reversed (36,122 concept edges tied and dropped), so its synset relations are not read; its
  pt antonyms are kept. Second build: relations unchanged, 3,000-word card comparison recorded in
  `01_own_pt.md` (304 best senses changed, a sample reads mostly worse; 15 lost, mostly junk).
- 2026-11-13 : the best-sense changes have two causes: own-pt's extra senses ranked by English
  commonness (202), and feminine and plural words own-pt lists only through another sense (about
  70), which the inflection rules skipped. Q10 (extend existing words) and Q11 (review and pin)
  answered; `15_inflection_model` Q5 narrowed. Forms fix in two tries: the first regressed
  feminine person nouns, the class rule fixes 7 cards and moves 10 feminine nouns to the
  adjective (review).
- 2026-11-13 : corpus rebuilt in place with own-pt; re-check batches `m0008` (90 words, gold 1/2,
  the *um* miss pinned by hand) and `m0009` (107 words, gold 2/2) after regenerating the pt
  worklist at 3,000 cards. After the rebuild 59 changed cards are still unreviewed: verbs below
  the worklist's rank 3,000 and their forms.
- 2026-11-13 : worklist at 7,800 and `m0010` (42 words, gold 2/2); a second, rule-only pass of
  the reviewed drops after the inflection stage, used for *paris*, *castro*, *acerca*. Every
  frequent pt card whose best sense moved is now reviewed or follows a reviewed base.
- 2026-11-13 : seed regenerated (742 lemmas, `make check` passes), look-alike losses read (58 pt
  words own-pt lacks, mostly junk; no action), doc counts updated. Phase review at the end: the
  corpus holds no own-pt definition or example (all 43,926 pt glosses are ours, 4 pt examples as
  before); findings raised as `00_start.md` Q12 (8,868 pt concepts with no pt gloss) and Q13
  (the notebook build records no source versions).
- 2026-11-13 : Q12 parked in `open_points.md`, Q13 done (`acquire.source_versions`, passed by the
  transform notebook); pt *é* had lost its only sense and is linked to "be" by a reviewed
  addition; seed refreshed again. Done-when verified: pt rows from own-pt, `_build.json` names
  `own-pt:1.0.0`, no own-pt text in the corpus, the 3,000-word comparison recorded,
  `make check` and `make docs-build` pass. Phase 1 done.
- 2026-11-13 : phase 2 reviewed before execution: the fr carve-out covers the whole local build,
  not only the seed; 170 "phase N" mentions in `src/`, of which phase 2 takes the five about
  licensing; `license-files` and a `uv build` check added; Q14 to Q16 raised.
- 2026-11-13 : Q14 (Pietro Maria Nobili), Q15 (licensing references only) and Q16 (lang-tutor
  branch `feat/license`) answered; phase 2 started.
