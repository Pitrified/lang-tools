---
status: done
priority: 0
description: |
  What a false friend's look-alike mainly means, as data: the main meaning of each en or it word
  that is a full or partial false friend of a pt word, so a card can say "it bravo means good"
  in the other language, and acerta can show *good* as the trap of pt *bravo* in an English round.
comment: |
  Asked from acerta's plan 03_false_friend_rounds (phase 4, its `00_start.md` Q10), on branch
  feat/03_false_friend_rounds of acerta-word-drills: the user, 2026-11-25, "we do it well,
  plan the change cross with lang-tools if needed".
---

# False-friend meanings - start

## Original note

acerta is a Portuguese pair-matching drill whose learner knows English and Italian.
The user, 2026-11-25: an Italian false friend trips them in an English round too, because they
"still pass through Italian": pt *bravo* means angry (it *arrabbiato*), it *bravo* means good,
so in an English round *good* is the trap.
acerta needs, for each false friend, a word for what the look-alike means, in the other known
language (it *bravo* -> en *good*; en *truck* -> it *camion*).
The user on the source: "we do it well".

## Current state

Measured read-only on the current corpus, 2026-11-25.

- A card's `LookalikeHint` carries `language`, `text`, `kind`, `note`. The note is English free
  text and often says the main meaning ("it bravo is mostly good or skilled, pt bom or
  competente"; "it burro is butter, pt manteiga"), but not as data.
- The built corpus holds 973 full or partial edges, over 847 distinct known words (an en or it
  word can be the false friend of several pt words).
  Corrected in phase 1: these first read 1,230 edges and 1,085 words, counted on
  `data/curated/lookalikes.jsonl`, whose latest rows include pairs the build drops as stale.
- Their senses in the lexicon:

  | Known language | One sense | Two or more |
  | -------------- | --------: | ----------: |
  | en             | 72        | 366         |
  | it             | 111       | 298         |

  84 of the 973 en hints have no it word for the look-alike's best sense
  ([`01.1_baseline_read.md`](01.1_baseline_read.md)).
- en senses carry their own frequency (en *novel*: *romanzo* 4.45 before *nuovo* 4.04);
  it senses share the word's frequency, so every sense ties (it *bravo*: brave / good /
  estimable, all 4.33) and nothing says which is the main one.
- A sense of the known word can be the meaning it shares with the pt word, which is what makes a
  partial false friend (it *novella*: news / **short story** / yarn, pt *novela* is a short story).
- Best-sense pins exist (`data/curated/best_senses.jsonl`, latest row per lemma, `concept_key`),
  written by the sense review for pt cards.

## Proposed approach

The main meaning is a property of the known word, not of the pair, so it is a best-sense pin
on the known lemma, reusing the existing mechanism, rather than a new field on the look-alike row.

1. **Worklist**: the known words of accepted full and partial edges.
   One sense: no row needed, the only sense is already the word's best sense.
   Two or more: reviewed.
2. **Review**: per known word, its senses with their words, and the pt words it is a false friend
   of; the reviewer picks the sense a speaker of that language means first, today.
   Rows go to `best_senses.jsonl` like the pt pins. A rulebook section or a short rulebook of its
   own (Q1).
3. **Card**: `LookalikeHint` gets `means`: the words of the look-alike's best sense (a pin, else
   the frequency pick, as its own card) in the card's other known languages, lead first (it *bravo* on an en card: `{"en": ["good", ...]}`).
   A frozen-API addition (a field with a default), so a new tag; lang-tutor ignores it.
4. **Gaps**: a pinned sense with no word in the other language gives an empty `means` there
   (Q2).

acerta then re-exports the cards (a card format bump on its side) and uses `means` for its
decoys; that part is acerta's.

## Open questions

- Q1: The review of the main sense: a section of the sense review (`docs/guides/sense_review.md`,
  `.claude/skills/sense-review/`) or a rulebook and skill of its own?
  - a. Its own: the question differs (the main sense of an en or it word, not a pt card's sense).
  - b. A section of the sense review, its batches under a new prefix.
  - Recommended: a, because the sense review's rules are about pt cards and its hash would change
    for rows that have nothing to do with them.
  - ANS: a, its own review. The user also asked whether this means running "a zillion senses again": no, see Q5.
- Q2: A pinned sense with no word in the other language (67 en words have none at all): what then?
  - a. Leave `means` empty there; acerta has no decoy from it.
  - b. The reviewer also writes the missing word, as a reviewed translation row.
  - Recommended: a for now, because it keeps this folder to one kind of row; b if acerta's
    numbers show the gap matters.
  - ANS: a: "then it's not in scope sadly"; such a look-alike gives a decoy only in rounds of its own language (an it one in pt/it rounds), as today.
- Q3: Review the en words with two or more senses too, though their senses have frequencies?
  - a. Yes, all 798 words with two or more senses.
  - b. Only the it ones (345), en by frequency.
  - Recommended: a, because a frequency picks the most common sense across all text, not the one
    a learner is trapped into (en *novel*, adjective "new" against the noun); "do it well".
  - ANS: a.
- Q4: Cost. About 8 batches of 100 words (798). By the agent-review measure (about 50 batches of
  100 for 60 session points), roughly 10 session points and 1 to 2 weekly points.
  To confirm on a first batch before the rest.
  - ANS: "not a problem for 10 session points". Still measured on the first batch before the rest.
- Q5: Does this re-run the sense reviews? (The user, 2026-11-25.)
  - ANS: no. Only the en and it words that are a full or partial false friend are reviewed, 798
    of them (the 287 with one sense need no row: their only sense is already the pick); the pt sense reviews and their
    rows are untouched. The build re-applies every curated input as usual, which is a rebuild,
    not a re-review.

### Batch 2, from the phase plans (2026-11-25)

- Q6: A best-sense pin also sets the word's part of speech to its pinned sense's
  (`apply_pinned_part_of_speech`), and moves what the en or it word's own card shows.
  Pinning 798 en and it words does both for them.
  - a. Accept: the main meaning is the right card sense for those words too; phase 5 counts the
    part-of-speech changes.
  - b. Keep the pins of this review out of the part-of-speech step and the card pick: a file or
    a flag of its own, read only by `means`.
  - Recommended: a, because the pick is the same question ("what does this word mean first") and
    one answer per word keeps the corpus consistent; b only if phase 5's count shows harm.
  - ANS: a (all recommendations taken, 2026-11-25).
- Q7: Order: `means` on the cards first (phase 1, before any review, using the current pick),
  then the review?
  - a. Yes: cheap, testable on the seed, gives acerta the field early and a baseline to compare.
  - b. Review first, field last.
  - Recommended: a, because the field does not depend on the review, only its words do.
  - ANS: a.
- Q8: `means` on cognates too? A cognate's main meaning is the pt word's, so it adds nothing.
  - a. False friends only (`full`, `partial`); empty on cognates.
  - b. Every look-alike.
  - Recommended: a, because nothing reads it on a cognate and it keeps the card small.
  - ANS: a.
- Q9: The batch prefix of this review in `best_senses.jsonl` (the sense review uses `s`, `m`,
  `n`): `f` (`f0001`)?
  - a. `f`.
  - b. Another letter.
  - Recommended: a.
  - ANS: a.
