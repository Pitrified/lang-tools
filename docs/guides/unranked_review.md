# Reviewing unranked pt words

wordfreq has never seen about five thousand single-word pt lemmas, so the CEFR score has nothing
to place them by.
They are a mix: words a learner meets every day (*peúga*), real words only a specialist or an
old text uses (*conquiliologia*), and entries that are not words a drill should teach at all
(a misspelling, a word of another language, two words glued together).
Each is labelled by an agent following these rules.
The real words get a commonness bucket that stands in for the missing frequency; the others are
dropped from the corpus at build.
This page is the rulebook every batch is labelled against: its hash is stored on every row
the review writes, so change it deliberately.

The tooling is `lang_tools.lexicon.ingestion.unranked_review` (worklist, batches, validation) and
its command line `unranked_review_cli`; the agent workflow is the `unranked-review` skill under
`.claude/skills/`.

## What to decide

Each item is one pt word, its part of speech, and one line per concept it is linked to:
the concept's English gloss and up to six of its English members.
The glosses are a hint to what the entry was meant to be, not proof that the word is real:
a misspelling or a foreign word inherits the gloss of the word it stands for.
Judge by Portuguese as written and spoken today, in Portugal and in Brazil.

Give every word exactly one label:

| Label | When |
| --- | --- |
| `c` | Common. A learner in Portugal or Brazil meets the word in everyday life or ordinary reading: *peúga*, *pigarrear*. |
| `u` | Uncommon. Real Portuguese, in educated or written register, that a learner meets in books, news or careful speech but not every day: *psicanalisar*, *metalizar*. |
| `r` | Rare. Specialist, technical, taxonomic or archaic: *conquiliologia*, *joeirar*, *xenótimo*. |
| `m` | Misspelled, or a non-standard spelling. Give the correct spelling: *magestoso* -> *majestoso*; an accent error such as *miseràvel* -> *miserável*. |
| `f` | Not Portuguese. Give the language code of the word: *walkout* `en`; *voluto* `it`. |
| `x` | Malformed: glued or broken text that is no word of any language: *canodachaminé*. |

`c`, `u` and `r` keep the word, in a commonness bucket; `m`, `f` and `x` drop it.
When two of `c`, `u`, `r` seem to fit, take the rarer one if a typical adult native speaker
would stop on the word, the commoner one if they would read past it.

## Rules for the hard cases

- **Valid regional spellings are not misspellings.** pt-PT and pt-BR spell some words
  differently, and both are right: *axónio* and *axônio*, *peúga* (pt-PT "sock", pt-BR *meia*),
  *facto* (pt-PT "fact") and *fato*, *túlipa* and *tulipa*, *dendrite* and *dendrito*.
  Label them by commonness (`c`, `u`, `r`), not `m`. Before calling a word `m`, ask whether a
  pt-PT or a pt-BR dictionary lists it as written: if either does, it is not `m`.
- **A spelling from before the 1990 spelling agreement is `m`.** *acção*, *óptimo*, *director*
  are no longer standard in either variety; give the current spelling (*ação*, *ótimo*,
  *diretor*). The build respells such forms itself where it can, so one that reaches you was
  missed.
- **An accent error is `m`.** *miseràvel* (grave instead of acute) and a missing or extra accent
  on a word that has a single standard form are misspellings; give the standard spelling.
- **`m` needs a clear target.** *ompletamente* is `m` -> *completamente* because the intended
  word is plain. When a form could be a typo of several words, or of none, it is `x`.
- **Use the glosses to find the intended word.** A misspelling is linked to the gloss of the word
  it was meant to be (*magestoso* "majestic"); that tells you the spelling to give. When the
  gloss names a common word one letter or accent away from the entry, the entry is `m` of that
  word, not a rare word of its own: *breio* glossed "bridle" is `m freio`, *éolico* is
  `m eólico`, *encrustar* is `m incrustar`.
- **Glued compounds.** A compound Portuguese writes with hyphens, stored with them missing
  (*palavrascruzadas*, *folhadelata*), is `m` with the hyphenated spelling
  (`m palavras-cruzadas`). A glued phrase that is not one compound (*tiradecouro*,
  *cartadecrédito*) is `x`.
- **Loanwords used in Portuguese are real words.** *hockey*, *mouse*, *sushi*, *software*,
  *marketing* are used in pt text: bucket them (`c`, `u` or `r`), do not drop them. A foreign
  word is `f` only when Portuguese does not use it: a word that is used in an English or Italian
  sentence but that pt text would translate or never use (*walkout*, *hockeyarena*, *pahoehoe*).
  When the entry is a foreign spelling of a word Portuguese does spell its own way, it is `m`
  with the Portuguese spelling.
- **Vulgar and offensive words are real words.** Bucket them; never drop a word for being rude.
- **Abbreviations and acronyms.** A lowercase abbreviation or acronym that Portuguese uses as a
  word (*sida*, *laser*, *radar*, *ovni*) is real: bucket it. A bare abbreviation with a full stop
  or a letter code that is not read as a word is `x`.
- **Lowercase proper nouns.** A name stored in lowercase (*brasil*, *angola*, a person or a
  place) is a real word in the wrong case, not a spelling error; it is not a vocabulary word a
  card should teach, so label it `x` with the reason `proper noun, stored lowercase`.
  A common noun that is also a name (*natal*, *índia* as a woman) is a real word: bucket it.
- **Inflected forms.** A conjugated verb or a plural that is a real Portuguese form is a real
  word; bucket it as the base word would be.
- **Archaic and dialect words** are `r`, not `m`, when they were once standard (*vossemecê*).
- **Latin and scientific names.** A form that is plainly Latin, with a Latin ending or spelling
  Portuguese does not use (*sphyraenidae*, *polyporaceae*, *paronychia*, *verbascum*), or a legal
  Latin phrase, is `f` with code `la`. A Portuguese word that also names a genus is Portuguese:
  *coccinela* (the ladybird) is `r`, not `f la`. A Portuguese taxonomic term (*conquiliologia*,
  *xenótimo*) is `r`.
- **Brazilian and European words differ in commonness.** Label by whichever variety uses the word
  more: *peúga* is `c` because it is everyday in Portugal even though Brazil says *meia*.
- **When you do not know the word,** look at the gloss and the English members: a technical gloss
  (a mineral, a species, a legal term) is `r`; a gloss of an everyday thing is `c` or `u`.
  A word you cannot place at all, with no sensible reading, is `x` with the reason `unknown form`.

## Reasons

`m`, `f` and `x` need a short English reason after `#`, saying what is wrong, so a later reader
can check it without the batch:

- `m majestoso # missing j`
- `f en # English loanword Portuguese does not use`
- `x # two words glued together`

Keep it to one line, under 120 characters, with no em dashes. `c`, `u` and `r` need none;
a comment after `#` on them is kept in the log (use it for a word you are unsure of).

## Label format

One line per item: the item number, the label, the extra the label takes, then `#` and the reason.
Blank lines and lines starting with `#` are ignored. Every served item needs exactly one line:

```text
1 c
2 u
3 r # a mineral
4 m majestoso # missing j
5 f en # English loanword, pt says "saída"
6 x # two words glued together
```

- `m` takes the correct spelling right after the label: one lowercase word, no spaces; a
  compound keeps its hyphens (`m palavras-cruzadas`).
- `f` takes the language code of the word right after the label: two or three lowercase letters
  (`en`, `it`, `es`, `fr`, `la`).
- `c`, `u`, `r` and `x` take nothing before the `#`.
- `m`, `f` and `x` need a reason after `#`.

`apply` refuses the whole batch if a line is missing, a number appears twice or is not in the
batch, a label is not one of the six, `m` has no spelling (or more than one word), `f` has no
language code, `c`, `u`, `r` or `x` has an extra, or `m`, `f` or `x` has no reason, and it lists
every problem at once. Fix the labels and run it again.

## What the labels do

Every label is logged in `data/curated/unranked_review_log.jsonl`, with the rulebook hash.
`m`, `f` and `x` append one drop row per concept link to `data/curated/member_form_drops.jsonl`
(kind `unranked`), so the next build removes the word; `c`, `u` and `r` append a row to
`data/curated/commonness_buckets.jsonl`.
In both files the latest row of a word wins.
