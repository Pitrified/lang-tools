# implementation tracking

Fix the pt cards whose right meaning is not linked, and bring back the frequent words the card
review removed, through a new curated input of sense additions applied at build. Measured
before and after on the pt top 1,000 cards. Analysis and decisions in
[`00_start.md`](00_start.md).

## Key decisions

- All fixes land in lang-tools; lang-tutor only bumps its pin (user, 2026-11-06).
- Decisions rest on at least 500 targeted corpus items: the pt top 1,000 cards and the 60
  removed lemmas, reviewed in full before and after (user, 2026-11-06).
- Reviewers (Q8 a): one agent per batch with hidden gold, plus one measured blind second
  review of 500 targeted items; the user reads numbers, not Portuguese.
- lang-tutor is never a blocker to a lang-tools change (user, Q7).
- One mechanism for every fix: an addition row (link + pin), plus the existing drops and pins;
  the review harness of `12_card_senses` is extended, not copied.

## Phases

| #  | Phase                 | Plan                               | Status  |
| -- | --------------------- | ---------------------------------- | ------- |
| 1  | Tooling               | [`01_tooling.md`](01_tooling.md)   | planned |
| 2  | Agent review          | [`02_review.md`](02_review.md)     | draft   |
| 3  | Rebuild and re-count  | [`03_recount.md`](03_recount.md)   | draft   |
| 4  | Release v0.4.0        | [`04_release.md`](04_release.md)   | draft   |

Status values: draft / planned / in progress / done / superseded / discarded.

## Log

Append-only. Newest at the bottom.

- 2026-11-05 : folder spun off from `12_card_senses` (its Q8) as a draft word list.
- 2026-11-06 : widened on the user's request to fix the 16 doubtful pt cards here, on branch
  `feat/13_missing_senses`. Read against the corpus: all 16 need a new link (none a change to
  the translation rule); *natal* and *índia* are capitalised-twin cases; the card review
  removed 60 pt lemmas; 28 of the 34 stale look-alike rows sit on them, 6 on closed-class words.
  Five draft phases, Q1 to Q6 raised. Measurement rule (500 or more targeted items) added.
- 2026-11-06 : Q1 to Q6 answered (both the verb link and the form; capitalisation, with
  lowercase proper nouns cleaned up; agents on top of agents; drop and clean up; es/fr out with
  a how-to guide; v0.4.0). Phases rewritten to four: tooling, agent review (which is also the
  baseline count), rebuild and re-count, release. Q7 raised: where the form note lives.
- 2026-11-06 : Q7 a (`Sense.form_note`, carried to the card). Q2 note: the lowercase proper
  nouns were a guess; causes will be tallied from the review's reasons. Q3 reopened (the phrase
  was sarcastic) and assessed from the logs as Q8: gold 424/465 on look-alikes but a noisy
  reference; the 24% of re-reviewed pairs that changed all followed rule changes; same-rules
  agreement never measured. Recommended one agent plus a blind second review of 500 items.
- 2026-11-06 : Q8 a. All questions answered; meta-experiments on the review method are welcome
  (the phase 2 measurement is the first). Phase 1 planned, phases 2 to 4 draft.
