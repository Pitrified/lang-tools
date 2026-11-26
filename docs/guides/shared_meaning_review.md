# Reviewing shared meanings of false friends

A pt drill card names its look-alikes in the learner's other languages, and a false friend's
hint carries what the look-alike mainly means (`LookalikeHint.means`): pt *bravo* is "angry",
it *bravo* is "good", so a drill that asks in English can offer *good* as the trap.
That trap only works when the pt word does not mean it too.
For a partial false friend it often does: it *tardi* mainly means "late", and pt *tarde*,
mostly "afternoon", is also "late" (*chegar tarde*), so *late* is a right answer, not a trap.
The pt word's senses in the corpus cannot settle it (they miss uses speakers make every day),
so each full and partial false-friend pair is read by an agent following these rules.

This page is the rulebook every batch is labelled against: its hash is stored on every row the
review writes, so change it deliberately.

The tooling is `lang_tools.lexicon.ingestion.shared_meaning_review` (worklist, batches,
validation) and its command line `shared_meaning_review_cli`; the agent workflow is the
`shared-meaning-review` skill under `.claude/skills/`.
The rows go to `data/curated/shared_meaning_log.jsonl`, which the build applies
(`ingestion.shared_meanings`): an `s` row sets `LookalikeHint.shares_meaning` on that pair.

## What to decide

Each item is one pair: a pt word and an en or it look-alike, then:

- the edge's kind (`full` or `partial`) and its learner note, which often says what each word
  means;
- the pt word's senses, one per line: the English gloss and the sense's en and it words; the
  first line is what the pt card shows;
- the look-alike's main meaning: its gloss and its words in pt, en and it. This is the meaning
  the drill would offer as the trap.

Ask one question: **do Portuguese speakers use the pt word for the look-alike's main meaning?**
Judge by Portuguese as spoken and written today, Brazilian or European.
The pt word's senses are evidence, not the answer: a use speakers make is a use even when no
sense line shows it, and a sense line for a use nobody makes does not count.

Give every item exactly one label:

| Label | When |
| --- | --- |
| `s` | Shared: the pt word is used for that meaning, as its main meaning or a secondary one in ordinary use (pt *tarde* "late"; pt *quarto* "fourth"; pt *lobo* "lobe", as in *lobo frontal*). |
| `d` | Distinct: the pt word is not used for that meaning; speakers say it with another word (pt *letra* is never a letter you send, that is *carta*; pt *time* is only a team). |
| `w` | Wrong: the main meaning shown is not what the look-alike mainly means (it *terza* shown as a baseball position, when it is mainly "third"). Say what it mainly means after `#`. |

Add `!` right after the label (`s!`, `d!`) when the item is a judgement call a human should
look at. Put a short reason after `#` on any label; `w` needs one.

## Rules for the hard cases

- **Secondary meanings count.** The pt word need not mainly mean it: one ordinary use is
  enough for `s`, because a learner who taps that word is not wrong (pt *bravo* also means
  brave, so en *brave*'s "courageous" is `s`).
- **Rare, archaic or one-phrase uses do not.** A use found only in old texts, in one fixed
  phrase, or in one trade's jargon is `d` (`d!` when you hesitate): a learner never meets it.
  A technical use in common speech, such as anatomy or music that a school reader knows
  (pt *lobo* "lobe", pt *sol* "the note G"), is `s`.
- **Regional use.** A use common in Brazil or in Portugal counts; a use from one region of
  either is `d!`.
- **The word, not a relative.** Judge the pt word as given, in its part of speech: pt *espera*
  (a waiting) is judged as the noun, even though the verb *esperar* also means "to hope". An
  inflected form (pt *precisa*, *preciso*) is judged by all the uses that spelling has.
- **Meaning, not words.** Compare the meaning with what the pt word means, not the en or it
  words with the pt word's translations: pt *próprio* and en *proper* share "suitable" even
  when no word is the same.
- **Full pairs are read the same way.** A full false friend should share no everyday
  meaning; when it does (pt *sorte*, "luck", is also "a kind" in *toda sorte de*), label it `s`
  anyway; the review of the look-alike kind is a separate job.
- **Wrong is about the main meaning, not the trap.** Use `w` only when the shown meaning is not
  the look-alike's main meaning in its own language. A right main meaning that makes a poor
  trap, or has poor words, is still `s` or `d`.

## Label format

One line per item: the item number, the label, an optional `!`, and a reason after `#`.
Blank lines and lines starting with `#` are ignored.

```text
1 s # chegar tarde
2 d
3 d! # only in Minas Gerais
4 w # it terza is mainly "third" (fem.), not the baseball position
```

## Gold set

`data/curated/shared_meaning_gold.jsonl` holds 50 hand-labelled pairs, each with its right
label. They go first in the worklist, so the first batch carries them unmarked;
`shared_meaning_review_cli gold` reports the agreement.
