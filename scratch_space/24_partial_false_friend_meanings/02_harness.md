---
status: done
---

# Phase 2 - Rulebook and harness

## Overview

The review tooling, copied from `false_friend_meaning_review`.
Linear after phase 1: `apply` writes the row model phase 1 defines.
Context: [`00_start.md`](00_start.md) (Q1, Q3, Q4); depends on
[`01_flag_on_cards.md`](01_flag_on_cards.md).

## The labels

One per pair (pt word, en or it look-alike):

- `s`: Portuguese speakers use the pt word for the look-alike's main meaning (as its main or a
  secondary meaning in ordinary use); the build flags the pair.
- `d`: they do not; no flag.
- `w`: the main meaning shown is not what the look-alike mainly means; no flag, a reason
  required; the log lists the pair for a later fix.

Each may carry `!` (an edge case) and a reason after `#`.

## Current state

- `ingestion/false_friend_meaning_review.py` and `false_friend_meaning_review_cli.py` are the
  template: worklist from a paged trap-card query (`build_worklist`), `serve_batch` /
  `recheck_batch` reserving under a locked work folder (`review_batches`), `render_batch`,
  `parse_labels`, `apply_batch` (nothing written if any label is bad, `LabelError` listing every
  problem), `gold_agreement`, `review_status`; tests in
  `tests/lexicon/ingestion/test_false_friend_meaning_review.py`.
- Phase 1's `SharedMeaningRow` (`ingestion/shared_meanings.py`) is the row `apply` writes to
  `data/curated/shared_meaning_log.jsonl`; that file is both the review log and the build input.
- Written by hand for this phase, already in the tree: the rulebook
  `docs/guides/shared_meaning_review.md` and the gold file
  `data/curated/shared_meaning_gold.jsonl` (50 rows: `target_id`, `target_text`, `known_id`,
  `known_text`, `known_language`, `label`, `reason`).

## Plan

1. `ingestion/shared_meaning_review.py`, on `review_batches`, following the template:
   - worklist file `work/shared_meaning_worklist.jsonl`, work folder
     `work/shared_meaning_review`, 100 items a batch, batch ids `p0001` up;
   - `SharedMeaningGold` (the gold row above) and `load_gold`;
   - `build_worklist(store, gold_pairs=...)`: every full and partial edge between a pt card and
     an en or it word, reached as the template reaches them; one item per pair, ranked gold
     first, then the pt card's frequency (most frequent first), then the look-alike's language
     and text. A work item holds the pair's ids and texts, the language, the kind, the frequency;
   - an item shows: the pair and its kind; the edge's note; the pt word's part of speech and
     senses (`lemma_sense_cards` with en and it words, the card's sense first); the look-alike's
     main meaning, its best sense (`lemma_card`): gloss and words in pt, en, it, itself left
     out. A look-alike with no sense shows `(no sense)`;
   - render, one item:

     ```text
     12 pt tarde (noun) ~ it tardi (partial)
       note: pt "tarde" is mostly afternoon, also late; it "tardi" is only late
       pt senses: 1 the part of the day between noon and evening [en: afternoon | it: pomeriggio]
                  2 ...
       it tardi mainly means: later than usual or than expected [en: late, belatedly]
     ```

   - `parse_labels`: `s`, `d`, `w` with optional `!` and `#` reason; `w` without a reason, a
     missing, repeated or unknown item number are problems;
   - `apply_batch`: one `SharedMeaningRow` per item (`model` = `REVIEW_MODEL`, `rulebook_sha`
     from the guide), appended to the log; the pending batch removed;
   - `recheck_batch`: words given as `pt_text:language:known_text` (`tarde:it:tardi`), only
     pairs with a label already; the new label wins;
   - `gold_agreement`: the latest label per gold pair against its gold label, misses listed as
     `pt tarde ~ it tardi: s -> d`;
   - `review_status`: worklist size, labelled, counts per label and edge cases, pending batches.
2. `ingestion/shared_meaning_review_cli.py`: `worklist`, `serve`, `recheck`, `apply`, `gold`,
   `status`, as the template's CLI.
3. The skill `.claude/skills/shared-meaning-review/SKILL.md`, a copy of
   `false-friend-meaning-review`'s adapted to this review (ids `p0001`, the label set, the
   files to commit: the log and the label files under `data/work/shared_meaning_review/`).
4. Docs: the rulebook in the `mkdocs.yml` nav next to the false-friend meaning one;
   `docs/library/lexicon.md`: the review tool in the paragraph on the shared meanings, and the
   curated-file table row (`shared_meaning_log.jsonl` written by the shared-meaning review).

## Tests

`tests/lexicon/ingestion/test_shared_meaning_review.py`, on a small store fixture (pt *tarde*
with a partial it *tardi* and a full en look-alike, plus a cognate that must not be listed):
the worklist lists the two false-friend pairs, gold first; serve reserves and repeats a pending
id unchanged, two batches never share a pair; render shows the pt senses and the main meaning;
a bad label set (a `w` with no reason, a missing item, an unknown label) is refused with every
problem and writes nothing; apply writes the rows and an `s` row then builds a flag through
`apply_shared_meanings`; recheck serves a labelled pair and refuses an unlabelled one; gold
agreement counts a miss.

## Out of scope

- Running batches (phases 3 and 4).

## Done when

- `make check` passes; `make docs-build` is clean.
- `CLI worklist` on the built corpus lists 973 pairs, the 50 gold first.

## What the implementation found

- Built by a Sonnet subagent at high effort, with each label defined in its prompt; code, tests,
  skill and label meanings were right first time; only a `lexicon.md` paragraph was reflowed.
- `recheck` serves every labelled pair matching `pt_text:language:known_text`, since one pt
  spelling can be two lemmas.
- The pt senses show en and it words; the look-alike's main meaning shows pt, en and it.
- `CLI worklist` on the built corpus: 973 distinct pairs, the 50 gold at ranks 0 to 49.
