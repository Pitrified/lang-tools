---
status: in progress
priority: 1
description: |
  Write the pt glosses missing since pt moved to OpenWordnet-PT: 8,877 concepts have a pt word
  and no pt gloss. Written by Claude subagents over served batches, like the look-alike tiers,
  instead of the paid OpenAI chain, and accepted by sampled review.
comment: |
  Moved here from scratch_space/open_points.md, "pt glosses for the concepts own-pt added".
---

# pt glosses - start

## Original note

From `scratch_space/open_points.md`, parked by [`18_licensing/00_start.md`](../18_licensing/00_start.md) Q12:
with pt from OpenWordnet-PT, pt words are linked to concepts that have no pt gloss;
the 2026-10 backfill covered the concepts omw-pt had.
Cards show the en gloss by default, so a learner sees the gap only with pt as gloss language,
which is the setting a pt-first fala will want.

On 2026-11-13 the user picked it up, and on the key question said:
"we run this like the tier B C D, using subagents. no api keys needed".
This box has no OpenAI key, and the paid chain is not needed for a job of this size.

## Current state

Measured on the 2026-11-13 build (`data/lexicon/`), read-only:

- `gloss_backfill.missing_glosses(data_fol, languages=["pt"])` returns **8,877** items
  (the dataset card says 8,868; the difference needs a look, see Q5).
  It also returns 3 fr / it items, the rows the October run left rejected; out of scope here.
- English glosses average 43 characters; each item carries up to 6 en and 6 pt member words
  as grounding, pt forms included (*totalizando*, *totalizar*).
- `data/curated/gloss_backfill.jsonl` holds 174,351 rows: pt 43,926 accepted, 1 rejected,
  and the es, fr, it rows.
- The build fills gaps only (`maintenance.apply_gloss_backfill`): an accepted row is applied when
  the concept has no gloss in that language, normalized by `normalize_gloss`, tagged `llm`.
  Nothing in the build changes for this folder.
- The OpenAI path is `notebooks/lexicon_maintain/gloss_backfill.ipynb` with
  `llm.gloss_translate` and the prompt `prompts/gloss_translate/v3.jinja`.
  Its check cell does `write_jsonl(proposals, curated)`, which **replaces** the curated file with
  the new run's rows; harmless in October (first run), wrong for any second run (Q6).
- The agent reviews share `ingestion/review_batches.py`: `locked` reservations, `append_rows`,
  `guide_sha` hashed into each row, work folders under `data/work/<review>/` (not committed).
  Each has a CLI (`serve`, `apply`, `status`), a guide in `docs/guides/`, and a skill in
  `.claude/skills/`.

## Proposed approach

A third agent job on the same plumbing, kept small because writing a gloss is simpler than a
review: no options to choose from, no corrections, no recheck.

- **CLI** `lang_tools.lexicon.ingestion.gloss_write_cli`:
  - `serve --batch g0001`: reserves the next 200 unserved items of the pt worklist under a lock,
    writes them to `data/work/gloss_write/g0001.jsonl`, and prints one line per item:
    `n | English gloss | en words | pt words`.
    Serving a reserved id prints it again.
  - `apply --batch g0001 --labels <file>`: reads `n<TAB>gloss` lines; refuses with
    `NOT APPLIED` and the problems when a number is missing, doubled or unknown, or when a gloss
    fails the existing `check_glosses` screen (empty, restates a pt word, untranslated, runaway
    length), so the agent fixes it rather than leaving a rejected row;
    on success appends one `GlossProposal` per item, status `proposed`, to
    `data/curated/gloss_backfill.jsonl`, and one line to a batch log (Q3).
  - `status`: served, applied, pending, items left.
- **Rulebook** (Q2): the v3 prompt's rules, which the October run was reviewed against.
- **Skill** `.claude/skills/gloss-write/SKILL.md`, the same shape as the other two:
  read the rules once, serve, write, apply, report in a few lines; and the orchestration note.
- **Acceptance**: rows land as `proposed`; after a review of a random sample
  (`gloss_backfill.review_sample`), `accept_run(..., languages=["pt"])` flips them, then rebuild.
  `accept_run` leaves the earlier accepted rows as they are.
- **No gold items** (Q4): the pilot read, the apply screen and the sampled review cover what gold
  does in the label reviews.

Size: 45 batches of 200. At the look-alike pace (a handful of subagents in parallel) this is a
few sessions of orchestration, no API spend.

## Phases (draft)

1. **Tooling**: the CLI, skill, batch log, tests; the notebook append fix (Q6); the 9 extra
   concepts explained (Q5).
2. **Pilot**: 3 batches (600 glosses), every one read by the orchestrating session against the
   English gloss, written up as an assessment for the user, before anything else is served.
   The rules change only if the pilot shows they must (Q2).
3. **Full run and rebuild**: the remaining 42 batches, a sampled review, `accept_run`,
   rebuild, quality gate (pt gloss coverage 100%), dataset card numbers, commit.

## Open questions

- Q1: Batch size.
  - a. 100 items per batch, 89 batches.
  - b. 200 items per batch, 45 batches; fewer subagent starts, longer contexts.
  - Recommended: a, because a gloss needs more care per item than a look-alike label, and the
    look-alike tiers settled on 100 for the harder tiers.
  - ANS: whatever the past subagent runs used. That is 200 (tiers B to D of
    `11_lookalike_review`, and `sense_review.DEFAULT_BATCH_SIZE`; the recommendation above
    misremembered 100): 45 batches, a 3-batch pilot.
- Q2: Where the rules live.
  - a. The agent reads `src/lang_tools/prompts/gloss_translate/v3.jinja` as is, and its hash goes
    on the log; one copy of the rules for both paths.
  - b. A new `docs/guides/gloss_writing.md`, written from v3 plus what the pilot teaches;
    the OpenAI path keeps v3. Two copies that can drift.
  - c. Move the rules to `docs/guides/gloss_writing.md` and have a v4 prompt include that file.
  - Recommended: a for the pilot, because nothing has shown the rules need to change;
    revisit after the pilot read if the agent needs rules the chain did not.
  - ANS: a; assess it on the pilot, on at least 500 glosses (the 3-batch pilot is 600).
- Q3: Provenance. `GlossProposal` has no model or rulebook field, and the OpenAI rows have none
  either.
  - a. A batch log `data/curated/gloss_write_log.jsonl`: batch id, rules hash, writer
    (`claude subagent`), date, counts, the keys written. Rows unchanged.
  - b. Add optional `writer` and `prompt_sha` fields to `GlossProposal`.
  - Recommended: a, because it mirrors the review logs and leaves a model shared with gloss
    repair alone.
  - ANS: a.
- Q4: Gold items. The reviews mix 2 hidden gold items into each batch to measure agreement.
  - a. None: free text cannot be scored automatically; quality is measured by the user's pilot
    read and the sampled review.
  - b. Hide 2 concepts per batch that already have an accepted pt gloss, and put the pair side by
    side in the review sample.
  - Recommended: a, because b produces a comparison to read, not a score, and the review sample
    already is one.
  - ANS: the user asked whether the pilot, reviewed by the orchestrating session, would become
    the gold, and whether gold is needed. Settled as a: gold scores a label against a known
    answer, and a written gloss has none; the pilot read sets the quality bar, the apply screen
    catches the mechanical failures, the sampled review after the full run catches drift.
- Q5: The count is 8,877 now against 8,868 in the dataset card. Check where the 9 come from
  (likely concepts linked by the reviewed additions after the card was written) in phase 1, and
  update the card in phase 3.
  - ANS: ok.
- Q6: The notebook's check cell replaces the curated file on any second OpenAI run.
  - a. Fix it in phase 1: read the existing rows, append the new ones.
  - b. Park it in `open_points.md`.
  - Recommended: a, because it is a two-line change next to the code this folder touches, and
    the next person to run the notebook loses 174k rows without it.
  - ANS: a, "keep our results safe".
- Q7: Variety. The October pt glosses are Brazilian (`LANGUAGE_VARIETIES["pt"]`), because
  OpenWordnet-PT is.
  - a. Keep pt-BR, consistent with the 43,926 existing glosses.
  - b. European Portuguese for the new ones only.
  - Recommended: a; a switch of variety is a decision for all pt glosses at once, not for 17%.
  - ANS: a, pt-BR.

### Batch 2: after the pilot

From [`02.1_pilot_assessment.md`](02.1_pilot_assessment.md): 590 of 600 right, 6 with a small
flaw, 2 faithful to a broken English gloss, 2 wrong; the four corrected.

- Q8: The subagent report lists, by item number, every item whose English gloss looks truncated
  or a fragment (two of the four corrections came from such flags).
  - a. Make it a required line of the skill's report.
  - b. Leave the report as it is.
  - Recommended: a, because it costs nothing and points the review at the items most likely wrong.
  - ANS: a.
- Q9: Size of the sampled review after the full run (8,277 glosses left, 42 batches).
  - a. A random 500 of the full-run glosses, plus every item the subagents flagged.
  - b. A random 200, plus the flagged items.
  - Recommended: a, because at a 0.7% defect rate a 500 sample still finds 3 or 4, enough to
    tell whether the rate held, and it matches the bar for an assessment.
  - ANS: a.
- Q10: About 3% of the pilot's items have pt words that do not mean the concept (OpenWordnet-PT
  links on concepts the old pt wordnet lacked; list in the assessment).
  - a. A section in `open_points.md`, no action here.
  - b. Ask the subagents to list these too, by item number, to build a worklist for a later
    review.
  - Recommended: b, because the subagents already notice them and the list comes for free;
    the review itself stays out of this folder, parked in `open_points.md`.
  - ANS: b.
