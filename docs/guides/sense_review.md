# Reviewing card senses

A drill card shows one meaning of a word: its lemma's best sense, picked by frequency, then by
how common the concept is.
For the most frequent words that pick is often wrong, in three ways no rule can see:
the word is linked to a concept it never means (pt *seja* "are", the unit, where *seja* is a form
of *ser*), the right meaning is there and loses the pick (pt *tarde* "night"), or the right
meaning is not linked at all (pt *sim* has only "yea", "not only so, but").
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
An item marked `REMOVED` is a word an earlier review took out of the corpus; its lines are the
links that review dropped, and the question is whether the word should come back.
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
| `aKEY` | The meaning a learner meets most is not listed: link the word to concept `KEY` (found with `concepts`, below), and the card shows it. Combines with `dK`. |
| `k` on a `REMOVED` item | The word stays out. |
| `aKEY` on a `REMOVED` item | The word comes back, with that meaning. |

A `REMOVED` item takes `k` or `aKEY` only.

### Finding a concept

Look the meaning up by its plain English word:

```bash
SAMPLE_API_KEY=placeholder-not-a-secret uv run python -m \
  lang_tools.lexicon.ingestion.sense_review_cli concepts --word yes --language pt
```

Each line is a concept key, its gloss, its English members, and the pt words already linked to
it. Pick the concept whose gloss is the everyday meaning, not a technical or rare one; when none
fits, keep or drop as usual and say so in the reason (`no concept for "headquarters"`).

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
- **A missing meaning is added, not guessed around.** When the word's everyday meaning is not
  among its senses (pt *sim* "yes", *vinte* "twenty", *aí* "there"), add it with `aKEY`, and drop
  the wrong senses with `d` in the same line. Do not pin a near miss instead (pt *aí* is not
  "yonder").
- **An inflected form is linked to its base word's concept, with a form note.** The corpus has
  no inflection model, so pt *são* (the verb) is linked to "be", and the note says which form it
  is, in braces: `{3rd person plural present of "ser": they are}`. The note names the person,
  number and tense or mood, the base word, and the plain English form. Do this for forms in
  ordinary use; a real homograph that is also in ordinary use (pt *são* "healthy") keeps its
  sense as a later one.
- **Proper nouns are capitalised.** A card is a lowercase word, so a name never is one. A
  lowercase lemma whose meaning is a name (pt *brasil*, *angola*) is `x`, with the reason
  `proper noun, stored lowercase`; when the capitalised word is not in the corpus with that
  meaning, write it in the notes file (below). A lowercase word that is a real word with its own
  meaning keeps it (pt *natal* "native, of birth", *índia* "an Indigenous woman").
- **Anything else wrong** that these rules do not name: label it as best you can and say what is
  wrong in the reason. Reasons are read and tallied after the review, so say it plainly.
- **When you do not know the word well**, keep the card and mark the line `!`.

## Notes file

Some fixes are not about the item in hand. Write them to
`data/work/sense_review/<batch>.notes.txt`, one per line, for the orchestrating session to check
and apply:

```text
member pt yes bd8e673cb0cf the English word, not pt; "yes" is "sim"
proper pt Brasil 3742781dca07 Brazil, the country; stored only as lowercase "brasil"
```

`member` names a wrong pt member of a concept you looked up (the language, the word, the
concept key, why). `proper` names a capitalised word to link (the language, the word, the
concept key, what it is). Leave the file out when there is nothing to note.

## Reasons

A `d`, `x` or `a` needs a short English reason after the actions, saying why the senses are
wrong or why the added one is right, so a later reader can check it without the batch:

- `x a form of ser; "are" is the unit`
- `d1 never the night`
- `d1 a0123456789ab "yes" is the everyday meaning; "yea" is rare`

Keep it to one line, under 120 characters, with no em dashes. `k` and `p` need no reason.

## Edge cases

Mark a call you are unsure of with `!` right after an action (`k!`, `p2!`, `d3!`, `x!`, `aKEY!`). The label
still applies, and the flag lists it for a second look. Use it for genuine judgement calls, about
one item in twenty: a word you do not know well, a homograph whose rare reading might be in
ordinary use, two pins that seem equally good.

## Label format

One line per item: the item number, the actions, a form note in braces if any, then the reason.
Blank lines and `#` comments are ignored. Every served item needs exactly one line:

```text
1 k
2 p3
3 d1 a form of ser; "are" is the unit
4 p2 d1! never the night
5 x a form of ter; "ringworm" is a rare homograph
6 d1 a0123456789ab "yes" is the everyday meaning; "yea" is rare
7 a1a2b3c4d5e6f {3rd person plural present of "ser": they are} the verb is the frequent reading
```

`k` and `x` stand alone; `p`, `d` and `a` may appear once each, `p` and `a` never together (an
addition pins its own sense). `apply` refuses the whole batch if a line is missing, a number
appears twice, a sense number is out of range, a sense is both pinned and dropped, every sense is
dropped with `d` and nothing is added (use `x`), a drop or an addition has no reason, a form note
has no addition, a `REMOVED` item takes anything but `k` or `a`, an added concept does not exist,
or an addition names a closed-class word (the build keeps those without senses), and it lists
every problem at once. Fix the labels and run it again.

## Hidden gold

Each batch mixes in two lemmas of the gold set (`data/curated/sense_review_gold.jsonl`), which
look like every other item. Their labels are not applied. Each gold lemma lists the meanings a
right card may show, or none when every link is wrong, and the agreement compares the card the
label leads to, batch by batch, in `data/curated/sense_review_log.jsonl`. A batch with a gold
miss is the first place to look for a drifting reviewer.
