# Reviewing card senses

A drill card shows one meaning of a word: its lemma's best sense, picked by frequency, then by
how common the concept is.
For the most frequent words that pick is often wrong, in two ways no rule can see:
the word is linked to a concept it never means (pt *seja* "are", the unit, where *seja* is a form
of *ser*), or the right meaning is there and loses the pick (pt *tarde* "night").
The top cards of each language are reviewed in batches by an agent following these rules,
and the labels are applied to the corpus at build.
This page is the rulebook every batch is labelled against: its hash is stored on every reviewed
row, so change it deliberately.

The tooling is `lang_tools.lexicon.ingestion.sense_review` (worklist, batches, validation) and its
command line `sense_review_cli`; the agent workflow is the `sense-review` skill under
`.claude/skills/`.

## What to decide

Each item is one word with every sense the corpus links it to, numbered in the card's pick order:
**sense 1 is the meaning the card shows today**.
Each sense line is an English gloss and its top English translations.
Judge by how the word is used **today** (Brazilian Portuguese for pt).
The question is: when a learner meets this word in ordinary text, what does it mean, and is that
the meaning the card teaches?

| Label | When |
| --- | --- |
| `k` | Sense 1 is a meaning a learner meets often, and the best one to teach first. Nothing listed is wrong. |
| `pK` | Sense K is the meaning a learner meets most; sense 1 is real but rarer, or less useful first. |
| `dK,L` | Senses K and L are wrong links: the word never means that. The card then falls to the first sense left. |
| `pK dL` | Both: pin K and drop the wrong L. |
| `x` | Every sense is a wrong link. The word leaves the corpus (its card, its lemma page, its look-alikes). |

## Rules for the hard cases

- **A wrong link is a meaning the word does not have.** The usual cause is a form shared with a
  more frequent word the corpus does not hold: a verb form (pt *seja*, *tinha*, *olha*, *era*),
  a plural (pt *homens*), a letter or a unit symbol. Drop it, even when the sense list has
  nothing else.
- **A real but rare homograph of a frequent form is dropped too.** When the word's frequency
  plainly comes from a reading the corpus does not hold, and the linked meaning is rare or
  technical, the card would rank a rare word among the most common ones: pt *tinha* is ringworm
  in a medical text, but a learner meets it as "had" (a form of *ter*), so it is `x`.
  A homograph in ordinary use stays: pt *era* is "was", but also the noun "era, age", which a
  learner meets in plain text (*a era digital*), so the noun is kept and pinned.
- **Pin the meaning a learner meets most, not the first in a dictionary.** pt *tarde* is
  "afternoon" and "late"; "night" is wrong (`d`), and either of the right two is a fine pin.
  When two senses are near-duplicates (two glosses of "evening"), pin the plainer one and leave
  the other; it is not wrong.
- **A narrow sense of a broad meaning is not wrong.** A sense that is a special case of the
  word's everyday meaning stays, unless it is plainly another word (pt *bem* "rather, quite" is
  real: *bem grande*).
- **Translations are a hint, not the sense.** Judge the gloss. A sense whose gloss is right but
  whose first translation is odd is still right.
- **Drop only what is wrong.** A real meaning that is rare, technical or regional stays as a
  later sense: it does no harm there. `d` and `x` are for meanings the word does not have, and
  for the rare-homograph case above.
- **Pin rather than drop** when sense 1 is real but not the best first meaning.
- **Grammatical words** keep their real senses like any other word: pt *um* is "one" and "a
  little" (*um pouco*); pin "one" when it is not sense 1.
- **When you do not know the word well**, keep the card and mark the line `!`.

## Reasons

A `d` or `x` needs a short English reason after the actions, saying why the senses are wrong, so
a later reader can check a drop without the batch:

- `x a form of ser; "are" is the unit`
- `d1 never the night`

Keep it to one line, under 120 characters, with no em dashes. `k` and `p` need no reason.

## Edge cases

Mark a call you are unsure of with `!` right after an action (`k!`, `p2!`, `d3!`, `x!`). The label
still applies, and the flag lists it for a second look. Use it for genuine judgement calls, about
one item in twenty: a word you do not know well, a homograph whose rare reading might be in
ordinary use, two pins that seem equally good.

## Label format

One line per item: the item number, the actions, then the reason for a drop.
Blank lines and `#` comments are ignored. Every served item needs exactly one line:

```text
1 k
2 p3
3 d1 a form of ser; "are" is the unit
4 p2 d1! never the night
5 x a form of ter; "ringworm" is a rare homograph
```

`k` and `x` stand alone; `p` and `d` may appear once each and combine. `apply` refuses the whole
batch if a line is missing, a number appears twice, a sense number is out of range, a sense is
both pinned and dropped, every sense is dropped with `d` (use `x`), or a drop has no reason, and
it lists every problem at once. Fix the labels and run it again.

## Hidden gold

Each batch mixes in two lemmas of the gold set (`data/curated/sense_review_gold.jsonl`), which
look like every other item. Their labels are not applied. Each gold lemma lists the meanings a
right card may show, or none when every link is wrong, and the agreement compares the card the
label leads to, batch by batch, in `data/curated/sense_review_log.jsonl`. A batch with a gold
miss is the first place to look for a drifting reviewer.
