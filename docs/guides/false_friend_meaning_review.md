# Reviewing what a false friend mainly means

A pt drill card names its look-alikes in the learner's other languages, and a false friend's
hint carries what the look-alike itself means (`LookalikeHint.means`): pt *bravo* is "angry",
it *bravo* is "good", so a drill that asks in English can offer *good* as the trap.
That meaning is the look-alike's best sense, which the build picks by frequency, then by how
common the concept is.
Italian senses all share the word's frequency, so commonness alone picks, and it *dito* shows
"toe"; an English word's frequency is split across its senses from a tagged corpus, and still
picks a rare sense now and then (en *font* "baptismal font").
Each en and it word that is a full or partial false friend of a pt word and has two or more
senses is read by an agent following these rules, which picks the sense a speaker of that
language means first.
This page is the rulebook every batch is labelled against: its hash is stored on every row the
review writes, so change it deliberately.

The tooling is `lang_tools.lexicon.ingestion.false_friend_meaning_review` (worklist, batches,
validation) and its command line `false_friend_meaning_review_cli`; the agent workflow is the
`false-friend-meaning-review` skill under `.claude/skills/`.
The rows are best-sense pins in `data/curated/best_senses.jsonl`, the file the card-sense review
writes for pt cards: a pin also moves what the word's own card shows and gives the word the part
of speech of the pinned sense.

## What to decide

Each item is one en or it word, its part of speech, then:

- one line per pt word it is a false friend of: the pt word, `full` or `partial`, and the
  edge's learner note, which often names the main meaning already;
- one numbered line per sense, in the card's pick order: the English gloss, then the sense's
  words in pt, en and it (the word itself left out). Sense 1 is what the card shows today.

Ask one question: **when a speaker of the word's language uses this word, with no context, what
do they mean first?**
Judge by the language as spoken and written today: everyday Italian for an it word, everyday
English (British or American) for an en word.
The pt word is context for why the item is here, not part of the question.

Give every item exactly one label:

| Label | When |
| --- | --- |
| `k` | Sense 1 is the main meaning. Keep it. |
| `pK` | Sense K (2 or more) is the main meaning. Pin it: it *dito*, sense 2 "a finger or toe", is `p2` over sense 1 "toe". |
| `m` | The main meaning is not among the senses. Keep the current pick, and say what the main meaning is after `#`. |

Add `!` right after the label (`p2!`, `k!`) when the item is a judgement call a human should
look at. Put a short reason after `#` on any label; `m` needs one.

## Rules for the hard cases

- **The pick is about the word, not the pair.** When the main meaning is the one the word
  shares with the pt word (it *novella* is mostly a short story, like pt *novela*), pick it
  anyway. A partial false friend is often exactly that word.
- **Pick the sense whose words name the main meaning.** Two senses can be near each other
  (it *dito*: "toe" and "a finger or toe"); pick the one whose words a learner would read as the
  main meaning (*finger*, *dedo*), not the one with the closest gloss. When the right sense's
  words are poor but another sense's words name the main meaning well, still pick the right
  sense; the words are fixed elsewhere.
- **Part of speech.** Many words are a noun and a verb (en *turn*, *notice*, *time*). Pick the
  use a speaker means first, whatever its part of speech: en *time* is the noun, en *notice* is
  more often the verb. The pin gives the word that part of speech.
- **Register and region.** A slang, regional or technical sense is the main one only when it is
  what most speakers mean first (it *casino* "mess" is everyday Italian; it *cotta* "a crush" is
  more common than "boiling"). A sense that a dictionary lists first because it is the oldest is
  not the main one for that reason.
- **An interjection or a set phrase.** en *bravo* is mostly the interjection "well done"; when no
  sense has it, label `m` and say so.
- **Inflected forms.** A word that is also an inflected form of another (it *sete* is
  "thirst", and the plural of *seta*, "silk") is judged by its meaning as a word of its own:
  pick "thirst".
- **Ties.** When two senses are equally the main meaning, keep sense 1 if it is one of them
  (`k`), else pin the more concrete one, and mark the label with `!`.
- **Not the trap.** Do not pick the sense that makes the better trap or the better drill; pick
  what the word means.

## Label format

One line per item: the item number, the label, an optional `!`, and a reason after `#`.
Blank lines and lines starting with `#` are ignored.

```text
1 k
2 p3
3 p2! # the finger; "toe" is the dito del piede
4 m # the main meaning, a typeface, has no sense here
```

## Gold set

`data/curated/false_friend_meaning_gold.jsonl` holds hand-labelled words, each with the senses a
right label may choose (or none, for `m`). They go first in the worklist, so the first batch
carries them unmarked; `false_friend_meaning_review_cli gold` reports the agreement.
