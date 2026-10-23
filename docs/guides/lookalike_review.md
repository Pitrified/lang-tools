# Reviewing look-alike pairs

The look-alike generator proposes about 65k word pairs between Portuguese (the target, the language
being learned) and English or Italian (the known languages) whose spellings resemble each other.
They are reviewed in batches by an agent following these rules, then applied to the corpus as
look-alike edges. This page is the rulebook every batch is labelled against: its hash is stored on
every reviewed row, so change it deliberately.

The tooling is `lang_tools.lexicon.ingestion.lookalike_review` (worklist, batches, validation) and its
command line `lookalike_review_cli`; the agent workflow is the `lookalike-review` skill under
`.claude/skills/`.

## What to decide

Each item is one pt word and one known word, with a short sense list for each (dictionary hints,
often incomplete). Judge by how the words are used **today** (Brazilian Portuguese), not by
etymology. The question is: when a learner who knows the known word reads the pt word, does the
resemblance help them, mislead them, or not register at all?

| Letter | Kind | When |
| --- | --- | --- |
| `c` | cognate | The main everyday meanings are the same, even if one word has extra senses or a different register (pt *felicidade* / en *felicity*). This includes the same root in another word form whose meaning carries over: an adjective and its noun, a person and the field, a verb and its noun (pt *monarca* / it *monarchia*, pt *notar* / it *nota*). |
| `p` | partial false friend | They share a real meaning, but the main everyday meaning of one of them is something else (pt *balada* is a ballad, but mostly a night out in BR; pt *gota* is a drop, it *gotta* only gout). |
| `f` | full false friend | No everyday meaning in common, and the resemblance misleads: the same root with a drifted meaning (pt *procurar* is to search; it *procurare* to procure), or a near-identical spelling of a common known word (pt *deserto* / en *dessert*, pt *babá* / en *baby*). |
| `u` | unrelated | A coincidence nobody would fall for. Either the letters really differ (pt *mangual* / en *manual*), or the known word is rare or technical (pt *fraca* / it *frac*, pt *bola* / it *bolo*), or the words are related but their meanings are plainly distinct and do not get mixed up (pt *general* / en *generality*, pt *cappuccino* / en *capuchin*). |

## Rules for the hard cases

- **Spelling alone never makes a cognate.** Two common words spelled alike with different main
  meanings are `f` or `p`, whatever their origin (pt *malga*, a bowl / it *malga*, an alpine hut).
- **Near-identical means apart only by an accent, a doubled letter or a final vowel.** A
  different consonant is a real difference (pt *casa* / en *cast*). Near-identical pairs whose
  meanings differ are `f` when the known word is common, and `u` when it is rare.
- **Same root, drifted meaning:** `f` when the shared root no longer carries the meaning
  (pt *envio*, a shipment / en *envoy*). It is `u` when the forms differ enough that no one
  maps one onto the other.
- **Grammatical words are `u`.** A preposition, conjunction, article, pronoun or other function
  word is `u` against a content word it happens to resemble, because nobody reads one as the
  other (pt *com* / en *come*, pt *mas* / en *mass*, pt *sem* / it *seme*, pt *para* / en *par*).
  It is `f` or `p` only when the two share a root whose meaning drifted.
- **The known language's own cognate wins.** When the known language has a direct cognate of the
  pt word, a near-identical but different known word does not mislead, so it is `u`
  (pt *caso* / it *casa*: it has *caso*; pt *casa* / it *cassa*: it has *casa*).
- **Inflected forms count by their most frequent reading.** When a word is both a lemma and a
  common inflected form of another word, judge the reading a learner meets most often and mention
  the other in the note. pt *era* ("was") / en *era* is `f`; pt *amo* (mostly "I love", also
  "master") / it *amo* ("I love", also "hook") is `p`, because the frequent reading is shared.
- **Partial versus cognate:** ask whether the learner is misled *most of the time*. A shared but
  rare sense does not rescue a pair: pt *privada* (BR: toilet) / en *privacy* is `f`.
- **The sense lists are hints.** They miss everyday meanings (*regalo* shows only "muff") and
  sometimes belong to a rarer homograph. Your knowledge of the words wins.
- **Proper-noun or slang senses** count only when they are the everyday meaning (pt *balada*
  yes; an obscene slang sense of a common word, no).

## Notes

Every `f` and `p` needs a one-line English note for the learner. Say what the pt word means and,
when there is one, the pt word for the known word's meaning:

- `pt "parentes" means relatives; en "parents" is "pais"`
- `pt "privada" means toilet (BR); en "privacy" is "privacidade"`

Keep it to one line, under 120 characters, with no em dashes. A `c` or `u` gets no note.

## Edge cases

Mark a call you are unsure of with `!` right after the letter (`f!`, `u!`, `c!`). The row still
applies as labelled, and the flag lists it for a second look later. Use it for genuine judgement
calls, about one item in twenty, not as a hedge on every line. Typical edge cases:

- a near-identical pair where the known word is only moderately common (pt *fogo* / en *fog*);
- a pair that is `p` or `c` depending on the register you assume;
- an item whose pt word you do not know well.

## Label format

One line per item: the item number, the letter, the optional `!`, then the note for `f` or `p`.
Blank lines and `#` comments are ignored. Every served item needs exactly one line:

```text
1 c
2 u
3 f pt "parentes" means relatives; en "parents" is "pais"
4 p! pt "turno" is mostly a work shift; en "turn" is mostly "vez"
```

`apply` refuses the whole batch if a line is missing, a number appears twice, or a false friend
has no note, and it lists every problem at once. Fix the labels and run it again.

## Hidden gold

Each batch mixes in a few pairs from the 1000-pair gold set (`data/curated/lookalike_gold.jsonl`),
which look like every other item. Their labels are not applied. They measure agreement with the
gold set, batch by batch, in `data/curated/lookalike_review_log.jsonl`. A batch with several gold
misses is the first place to look for a drifting reviewer.
