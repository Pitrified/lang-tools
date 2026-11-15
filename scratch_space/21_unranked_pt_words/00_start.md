---
status: draft
priority: 1
description: |
  Sort the 8,597 pt words that have no wordfreq frequency (and stray non-pt words) with
  Claude subagents over served batches: real and common, real and rare, misspelled, not
  Portuguese, malformed. Drop the bad ones through curated input, and give the real ones a
  commonness the CEFR score can use instead of the mid-scale default.
comment: |
  Two open points of `20_rare_words_topics` (on `feat/20_rare_words_topics`, in its
  `scratch_space/open_points.md`): "pt words with no frequency" and "Stray non-pt words in
  pt". They move here; their entries come out of `open_points.md` once both branches meet
  on `main`.
---

# Unranked pt words - start

## Original note

From `20_rare_words_topics/00_start.md` Q5 (on `feat/20_rare_words_topics`), the user on
2026-11-15: "Flag as open point. We will spin off agents to categorize them. Also voluto
Is not Portuguese lol, another open point about stray words." Picked up the same day.

The CEFR score treats an unknown frequency as mid-scale (`enrich.NEUTRAL`), so a word
wordfreq has never seen lands in B2 or C1 (voluto, Italian for "wanted", is B2 and reached
acerta as "voluto - abandoned"). acerta's commonness floor keeps such words out of its
drills, but other consumers of the bands see them.

## Current state

Measured read-only on the 2026-11-15 build (the one of `20_rare_words_topics`, release
0.8.0 on its branch; this branch is cut from `main`, which is 0.7.0, so the measurement
is the newer corpus):

- 8,597 pt lemmas have no token frequency on any sense; 8,596 from `omw`, 1 `manual`.
  By part of speech: 6,425 nouns, 977 verbs, 745 adjectives, 450 adverbs.
- 4,814 are a single lowercase word; 3,783 are multiword or other.
- A 60-word sample of the single words holds every kind:
  - real and rare pt: coruscar, joeirar, conquiliologia, xenótimo, apostema;
  - real pt a learner meets: peúga, pigarrear, psicanalisar, metalizar;
  - misspelled: miseràvel, magestoso, ompletamente, temporiamente, despidir;
  - not Portuguese: walkout, hockeyarena, pahoehoe;
  - malformed: canodachaminé (glued words).
- The build already drops reviewed forms per lemma and concept through
  `data/curated/member_form_drops.jsonl` (376 rows, `apply_form_drops`).
- `19_pt_glosses` (on its branch) runs Claude subagents over served batches with no API
  key; the same harness pattern fits here.

## Approach

- A worklist of the 8,597 words with their glosses and English members as grounding.
- Claude subagents sort each word into a category, under a written rulebook whose hash is
  stored on every row, like the look-alike and sense reviews.
- A pilot of 500 words, read and measured (per-category counts and an agreement check on a
  hand-read sample), before the rest.
- What each category does in the build is the open question below.

## Open questions

- Q1: What should each category do in the corpus?
  - a. Misspelled, not Portuguese and malformed are dropped (member form drops); real words
    get a commonness bucket (common / uncommon / rare) that stands in for the missing
    frequency in the CEFR score, so a rare word lands in C2 and a common one lower.
  - b. Only the drops; real words keep the mid-scale default.
  - c. Drops, and every real word with no frequency is scored as rare, with no bucket.
  - Recommended: a, because it fixes both voluto (dropped) and words like peúga that are
    everyday pt-PT but missing from wordfreq, which c would push to C2.
  - NEW_ANS:
- Q2: The stray non-pt words that do have a frequency (an English or Italian word that
  wordfreq's pt list counts) are not in this worklist. Include them?
  - a. Not now: the 8,597 first; strays with a frequency are a later pass once the pilot
    shows how many non-pt words there are.
  - b. Yes: add a second worklist of pt words that also exist as an en or it word with the
    same spelling and no shared meaning.
  - Recommended: a, because the no-frequency set is where the sample found them, and a
    same-spelling worklist also catches real cognates and needs its own rules.
  - NEW_ANS:
- Q3: The multiword entries (3,783): sort them too, or only the single words?
  - a. Only the 4,814 single words: drills use single words, and multiword entries need
    different rules (phrase or not, idiom or definition).
  - b. All 8,597.
  - Recommended: a, because every consumer that drills reads single words, and the
    multiword ones are mostly specialist names.
  - NEW_ANS:
