# Reviewing the words of a meaning

A meaning (a WordNet concept) lists every word linked to it, and a pt card shows them: the
meaning's other pt words are the card's synonyms, and a word page lists them all.
Some of them are not other words for the meaning: a plural or an adjective's feminine stored as
a word of its own, a word that names something else, a definition pasted in as a word.
And a card pairs the first en word of its meaning, which the frequency picks, so an en noun that
is also a frequent verb form can lead (*calling* on *carreira*, where *career* is the word).
An agent labels both against these rules.
This page is the rulebook every batch is labelled against: its hash is stored on every row the
review writes, so change it deliberately.

The tooling is `lang_tools.lexicon.ingestion.meaning_review` (worklists, batches, validation)
and its command line `meaning_review_cli`; the agent workflow is the `meaning-review` skill
under `.claude/skills/`.

There are two kinds of batch: meaning batches (ids `w0001`, `w0002`, ...) label each pt word of
a meaning, lead batches (ids `l0001`, ...) the first en word of a meaning.

## Meaning batches

Each meaning starts with a header line, `== gloss`, and a line with the pt cards it is the meaning
of and its en and it words.
Then one numbered line per pt word: `n word (level part-of-speech)`, and in brackets what a rule
noticed: `plural of "canal"`, `feminine of "eterno"`, `capitalised`, `definition-like`.
The hints are leads, not verdicts: check each one.

Give every word exactly one label:

| Label | When |
| --- | --- |
| `k` | Keep. The word is a Portuguese word for this meaning: a learner who reads it here learns something true. |
| `f <base>` | A form of another pt word of this meaning, not a word of its own: a plural (*canais* of *canal*), or an adjective's feminine or plural (*eterna*, *eternas* of *eterno*). Give the base word as shown. |
| `d` | Drop the word from this meaning: it names something else, it is a definition rather than a word, a misspelled or capitalised duplicate, or not Portuguese. |

`f` keeps the word in the corpus as a form of its base: it leaves the cards and the meaning's
list of words, like the forms the build makes by rule (*anos* of *ano*).
`d` removes only this word's link to this meaning; its other meanings stay.

### Rules for the hard cases

- **A word is right for the meaning when a Portuguese speaker would use it for the gloss.**
  WordNet meanings are broad, so a near synonym, a register variant or a regional word is `k`:
  *profissão* and *ocupação* on "the particular occupation for which you are trained" are `k`.
  Drop only a word that would teach something false: *cachimbo* (a smoking pipe) on "a long
  hollow conduit" is `d`.
- **Plural-only and plural-meaning words are words.** *algemas* (handcuffs), *óculos*,
  *férias*, *costas* (the back) mean something their singular does not: `k`.
- **A noun for a person keeps both genders.** *amigo* and *amiga*, *afilhado* and *afilhada*,
  *agnóstico* and *agnóstica* name a man and a woman: both `k`. Their plurals (*amigas*
  beside *amiga*) are `f`.
- **An adjective's feminine and plurals are forms.** *eterna*, *eternos*, *eternas* beside
  *eterno*; *chocada* beside *chocado*: `f` with the masculine singular as the base.
  A past participle used as an adjective counts as an adjective.
- **`f` needs its base in the same meaning and the rules to make it.** `apply` checks that the
  base is another pt word of the meaning and that the build's inflection rules turn the base
  into the word. When the base is missing, or the rules do not make the form (an irregular
  plural), label the word `k`, or `d` when it should not be there at all.
- **pt-PT and pt-BR spellings are both right.** *académico* and *acadêmico*, *facto* and *fato*:
  both `k`.
- **A capitalised duplicate of a lowercase word is `d`.** *Aluminio* beside *alumínio*,
  *Bario*, *Argon*: the entry is a misspelled name of the element. A name the meaning is about
  (*Bíblia* on "the sacred writings") is `k`.
- **A definition is not a word.** *exigente sobre seu traje*, *admitir a veracidade de* are
  descriptions, `d`. An idiom or a fixed phrase Portuguese uses as a unit (*de cabo a rabo*,
  *vida após a morte*) is `k`.
- **Misspelled and foreign entries are `d`.** A spelling no pt-PT or pt-BR dictionary lists, a
  spelling from before the 1990 agreement, an English or Latin word pt text does not use.
- **Vulgar and offensive words are words.** Never drop a word for being rude.

## Lead batches

Each meaning is two lines: `n cards: gloss`, then `en: word | word | ...`, the meaning's en words
in the order a card shows them. The first is the current lead, the word a drill pairs with the pt
card.

| Label | When |
| --- | --- |
| `k` | Keep the order: the first word is a good English translation of the cards in this meaning. |
| `l <word>` | Lead with this en word instead: one of the words shown, written exactly as shown. |

- **Pick the word an English speaker would use to translate the card in this meaning.** *career*
  for *carreira*, *existence* for *existência*, *delivery* for *entrega*, *growth* for
  *crescimento*.
- **An -ing word that is the normal noun stays.** *building* for *prédio*, *meeting* for
  *encontro*, *training* for *treino*, *feeling* for *sentimento*: `k`.
- **An -ing adjective that is the right adjective stays.** *annoying* for *irritante*: `k`.
- **Only reorder.** When no word shown is a good lead, label `k` and say so in the reason; the
  review cannot add words.

## Reasons

Write a short English reason after `#`, one line under 120 characters, with no em dashes.
`d` needs one, saying what is wrong: `d # a smoking pipe, not a conduit`.
`k`, `f` and `l` take one when you are unsure; it is kept in the log.

## Label format

One line per numbered word (meaning batches) or meaning (lead batches): the number, the label,
the extra the label takes, then `#` and the reason.
Blank lines and lines starting with `#` are ignored. Every served number needs exactly one line:

```text
12 k
13 f canal
14 d # a smoking pipe, not a conduit
3 l career
4 k
```

`apply` refuses the whole batch if a line is missing, a number appears twice or is not in the
batch, a label is not one of the batch's, `k` or `d` has an extra, `d` has no reason, `f` names
no other word of the meaning or one the rules do not make the word from, or `l` names a word not
shown or the one that already leads; it lists every problem at once. Fix the labels and run it
again.

## What the labels do

Every label is logged in `data/curated/meaning_review_log.jsonl`, with the rulebook hash.
`f` appends a row with the form note to `data/curated/sense_additions.jsonl`, so the build tags
the link as a form; `d` appends a drop row for the one link to
`data/curated/member_form_drops.jsonl` (kind `meaning`); `l` appends a row to
`data/curated/lead_translations.jsonl`.
In each file the latest row of a key wins.
