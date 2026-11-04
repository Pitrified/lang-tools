---
status: in progress
priority: 0
description: |
  Make the most frequent drill cards teach the right meaning: two build rules (no card for a
  one-letter lemma, a word before a digit in translations) and an agent review of the top
  1,000 cards per language that drops wrong concept links and pins the right best sense.
comment: |
  Opened on 2026-11-03 from lang-tutor's scratch_space/03_ui_followups (phase 3, first cards),
  whose count found about 98 bad cards in the pt top 500; the user answered its Q11 a: all four
  fixes, with the review as its own lang-tools folder. lang-tutor's phase 3 re-lists the cards
  when this folder is done.
---

# Card senses - start

## The idea

The cards a learner meets most often show the wrong meaning. lang-tutor's phase 3 (first cards,
in its `scratch_space/03_ui_followups`) listed the 500 most frequent single-word cards in pt, es
and fr with every sense, and found about 98 of the pt 500 wrong, a third of the top 100. The
user chose to fix all four causes, with the review in a folder of its own (lang-tutor's
`00_start.md` Q11, a).

## The four causes, and where each is fixed

| Cause | pt, of 500 | Examples | Fix |
| ----- | ---------: | -------- | --- |
| One-letter lemma | 18 (es 8, fr 9) | pt *d*, *c* "one hundred", fr *g* "mobile phone" | rule: no card |
| Wrong link to a rare concept, so no right sense | about 25 | pt *seja* "are" (unit), *tinha* "ringworm", *olha* "bouillon", fr *a* "repel", *comment* "yak" | reviewed rows in `member_form_drops.jsonl` |
| Right sense exists but loses the pick | about 43 | pt *homens* "work force", *bem* "kind of", *tarde* "night", fr *un* "two" | reviewed best-sense override (new) |
| Sense right, first translation a symbol | 8 (es 4, fr 11) | pt *dez* "x", *dois* "2", fr *tel* "i" | rule: a word before a symbol |

The pt counts of the second and third rows are a reading, so they are estimates; the first and
fourth are counted by script.

## Current state

- **The best-sense pick** is in `lemma_store._derive_drill_table`: highest `sense_frequency`,
  then the more common concept (`Concept.commonness`), then the easier CEFR band, then the
  concept id. Outside English every sense of a lemma ties on frequency, so commonness decides,
  and a common concept reached through a rare reading wins.
- **Wrong links** can already be dropped: `member_form_drops.jsonl` holds reviewed
  `FormDrop` rows (lemma, concept key, drop, reason), applied at build by `apply_form_drops`; a
  lemma with no sense left is dropped. Its 163 rows came from an LLM job on the phase 8 loop.
  The closed-class rule (`ingestion/closed_class.py`) drops function words by list, and leaves
  out inflected verb forms on purpose, which are most of the wrong links.
- **Translations** are "most frequent first" (`_card_translations`), and wordfreq ranks *x*, *2*
  and *i* above *ten*, *two* and *one*.
- **The review harness** for look-alikes is the model for the new review: a worklist, `serve`
  and `apply` subcommands, a rulebook whose hash is stored on every row, hidden gold items, a
  skill for the subagent, 200 items per batch, latest row wins
  (`ingestion/lookalike_review.py`, `lookalike_review_cli.py`, `docs/guides/lookalike_review.md`,
  `.claude/skills/lookalike-review/`).
- **`Sense` is frozen** (`docs/library/frozen_api.md`), so a new field on it needs a tag and a
  pin bump in lang-tutor. lang-tutor's phase 5 already plans one release for this.

## Proposed phases

1. **Build rules:** no card for a one-letter lemma; translations put a word before a digit, a
   Roman numeral or a single letter. Tests. Code only.
2. **Override input and applier:** a curated `best_senses.jsonl` (lemma, concept, reviewer
   fields), applied at build so the drill table picks the pinned sense first.
3. **Review harness:** the worklist (top 1,000 cards per language, frequency order), the CLI,
   the rulebook, the skill and a small gold set; one reviewer row either keeps the pick, pins
   another sense, or drops wrong links.
4. **Review run:** the batches, then a rebuild and the gate.

## Open questions

- Q1: How the build pins a reviewed best sense, given that `Sense` is frozen.
  - a. A new `Sense` field, `is_best: bool = False`, set by the applier and ordered first by the
    drill table. Additive, so existing readers are unaffected; it goes in lang-tutor's planned
    release.
  - b. The applier raises the pinned sense's `sense_frequency` above the lemma's other senses.
    No model change, but the field then stops meaning a frequency.
  - c. A separate corpus table, `best_senses.parquet`, that the store joins when it derives the
    drill table. No model change, but a new corpus file to carry and document.
  - Recommended: a, because the field says what it means, and the release is happening anyway.
  - ANS: a. `Sense.is_best`, set by the applier, ordered first by the drill table (phase 2).
- Q2: Which languages the review covers.
  - a. pt, es and fr, 1,000 cards each (3,000).
  - b. pt only first (1,000), then es and fr if the pt batches go well.
  - c. pt, es, fr and it (4,000).
  - Recommended: b, because pt is the learner's language, and the first 1,000 measure the cost
    and the rulebook before the other two.
  - ANS: b. pt first, 1,000 cards; es and fr after it, if the pt batches go well.
- Q3: Who reviews.
  - a. Subagents on the harness, 200 cards a batch, one commit per round, as for look-alikes.
    Cost to measure on the first batch; a guess from the look-alike rate (about 600 pairs per
    weekly point, cards are longer) is 2 to 3 weekly points per 1,000 cards.
  - b. A paid LLM job on the phase 8 loop, as for the form drops: sample-measured and approved
    first.
  - Recommended: a, because the look-alike review showed agents follow a rulebook well, and it
    costs no API money.
  - ANS: a. Subagents on the harness; the first batch is measured and its cost reported before
    the rest.
- Q4: Whether the one-letter rule removes the lemma or only its card.
  - a. Only its card: the drill table skips a lemma of one character, so the lemma page and the
    lemma reads keep it.
  - b. The lemma, at build, like a closed-class word.
  - Recommended: a, because a letter is a real lemma, just not a drill.
  - ANS: a. Only the card: the drill table skips a one-character lemma, the lemma stays.
- Q5: Whether a real but rare homograph of a frequent form is dropped. pt *tinha* is ringworm
  in a medical text, but a learner meets it as "had" (a form of *ter*, which the corpus does not
  hold as a lemma). Its card ranks among the top 100 because the frequency comes from the verb.
  The rulebook (`docs/guides/sense_review.md`) currently says `x`: the lemma leaves the corpus,
  with its lemma page and look-alikes.
  - a. Drop it, as the rulebook says: the card is the harm, and a rare noun is no loss.
  - b. Keep the lemma and only remove its card (a new label and a new curated flag), so the
    word stays readable on its page.
  - c. Keep it: a real meaning is never dropped; the card stays.
  - Recommended: a, because b adds a second mechanism for a few dozen words, and c leaves the
    worst cards in place.
  - ANS: a. A rare homograph of a frequent form is `x`, as the rulebook says.
