---
status: done
priority: 0
description: |
  An inflection model for pt (and later the other languages): map an inflected form
  (*anos*, *foi*, *disse*) to its base word's card with a form note, by rule or table at
  build, instead of one reviewed row per form.
comment: |
  Spun off from 14_number_modal_words (on feat/14_number_modal_words), 00_start.md Q7 b and
  Q11 b. Picked up 2026-11-11 (user: "Go for inflection model. Plan it, execute it").
---

# Inflection model

## Origin

`14_number_modal_words` (branch `feat/14_number_modal_words`) found that the largest group
of frequent pt words absent from the corpus are inflected forms of a word the corpus has:
197 in the pt top 1,000, 262 in the 1,001 to 2,000 band, and about 1,300 in the top 5,000.
Its phase 5 gave the 187 forms of the top 1,000 a lemma each, linked to the base word's
concept with a form note (`plural of "ano": years`), through reviewed `sense_additions` rows
written by subagents. Every card came out right, but each form cost about 1,200 subagent
tokens and a checked line; the top 5,000 would be about 1.6M tokens, 5% to 10% of a weekly
limit, and the cost grows linearly with every form.
The user chose the model before any more rows (`14_number_modal_words/00_start.md` Q11,
answered b, 2026-11-10).

## The idea

A form is found and tagged by rule or table, not reviewed one at a time:

- generate or look up the forms of a base word (pt verb conjugation, noun and adjective
  plural and gender), with the grammatical label that becomes the form note;
- at build, link each frequent form to its base word's card (or to the concept a reviewed
  row chose, where the form means something else: *todos* "all", *pais* "parents");
- search: a learner typing *foi* finds *ser* and *ir*.

## Current state (measured 2026-11-11, v0.6.0 corpus)

- A form has a card only through a reviewed `sense_additions` row with a `form_note`:
  421 distinct pt words carry one, from `14_number_modal_words` phases 5 and 7 (the 187 content
  forms, plus the contractions and pronoun forms of the closed-class concepts: *do*, *na*, *mim*).
  The row creates the lemma, with the part of speech of the concept's lexfile.
- The build order (`ingestion/pipeline.py` `build_initial`): drops, concept additions, sense
  additions, glosses, examples, `enrich` (frequency and CEFR of every sense, from the lemma's
  `wordfreq` zipf), topics, look-alikes, best-sense pins, pinned part of speech.
- A card is the lemma's best sense (`lemma_store._derive_drill_table`): the pinned sense, else the
  highest `sense_frequency`, then `Concept.commonness`. Outside English every sense of a lemma
  ties on frequency, so a form that carries all of its base's senses gets its base's card, except
  where the base's card is a pin.
- The card carries the best sense's `form_note` (`lemma_drill.form_note`); no card filter reads it.
- A lemma is found by its deterministic id (`lemma_id(text, language)`); there is no text search
  endpoint, so "a learner typing *foi*" means a client computing the id of *foi*.

## Sources assessed

All three downloads went to the session scratchpad; nothing was committed.

- **UniMorph `por`** (CC BY-SA 3.0, from Wiktionary): 303,997 rows, verbs only (4,002 verbs, every
  finite form and the participles), no noun or adjective inflection.
- **kaikki.org Portuguese** (the wiktextract extract of the English Wiktionary, CC BY-SA 4.0 and
  GFDL; extracted 2026-10-30 from the 2026-10-01 dump; 582MB of JSONL, 447,028 entries): every
  form entry has a form-of sense naming its base word and tags (*anos*: `plural of ano`,
  `[masculine, plural]`; *foi*: `third-person singular preterite indicative of` *ir* and *ser*;
  *boa*: `feminine singular of bom`). 351,303 forms. One gap: about 5,900 verb glosses of the
  shape `third-person plural preterite/pluperfect indicative of ir` carry no form-of field (*foram*,
  *fizeram*, *tiveram*), so the gloss has to be parsed too.
- **Rules of our own** (the ending rules of `14_number_modal_words/01.1_gap_classify.py`): no
  licence question, but they propose wrong bases freely (*olha* from *olho*, *visto* from *vestir*)
  and need an irregular table for every frequent verb.

Measured against the 421 reviewed form words (their base is the word quoted in the form note):

- kaikki finds the reviewed base for 363; 16 get only another base, and 42 none.
  Nearly all of the 58 are closed-class words, which stay with their reviewed rows (*do*, *pelo*,
  *deste*, *mim*, *isso*), plus *dezasseis* (a spelling, not a form), *foram* and *fizeram* (the
  gloss gap), and *feita*, *usada*, *criada*, *última* (kaikki names the participle or the
  accented spelling: *feita* is a form of *feito*, itself a form of *fazer*).
- UniMorph plus the ending rules find 312 and miss the forms of *ser*, *estar* and *saber*,
  whose corpus lemmas are nouns.

The absent pt words that kaikki gives a base the corpus has, with a sense of the form's class
(a verb form needs a verb sense of the base), by `wordfreq` zipf of the form:

| zipf floor | forms  | verb  | noun  | adj   | several bases | also a word of its own |
| ---------- | ------ | ----- | ----- | ----- | ------------- | ---------------------- |
| 4.0        | 2,126  | 1,090 | 620   | 416   | 130           | 140                    |
| 3.5        | 5,381  | 2,864 | 1,407 | 1,110 | 252           | 299                    |
| 3.0        | 10,834 | 6,044 | 2,579 | 2,211 | 370           | 522                    |
| 2.5        | 17,783 | 10,202| 4,096 | 3,485 | 463           | 789                    |

The pt corpus has about 46,000 lemmas today. "Several bases" is mostly a noun plural that is also
a rare verb form (*formas*: *forma*, and *formar* "you form"; *causas*, *rodas*), a verb that is
also a rare verb (*vendem*: *vender*, *vendar*; *tivessem*: *ter*, *tar*), and a few true
ambiguities (*foi*, *fui*: *ser*, *ir*; *vira*: *virar*, *ver*; *cria*: *criar*, *crer*).
"Also a word of its own" means kaikki has a non-form sense too: *velha* "wife, mother",
*imagina* "no problem", *fechou* "OK", *frito* "screwed".

## Licence

`09_concept_model/05.4_data_quality.md` section 3 dropped kaikki in phase 5.5 to keep the
corpus free of share-alike data: one CC BY-SA field (a gloss, an example) pulls the shipped
dataset to CC BY-SA. Its own analysis separates facts from expression: "Our
concept/lemma/sense edges are low-risk; the license rides on the definitions/examples strings".
A form table is facts of that kind (*anos* is the plural of *ano*), and the form note text would
be written by our own code from the tags, so no Wiktionary text is copied. UniMorph is the same
data under CC BY-SA 3.0. What remains is the extraction of a substantial part of a database,
which some jurisdictions (the EU database right) protect apart from copyright; the CC BY-SA
licence permits it with attribution and share-alike on the database. This is a judgement for the
user, raised as Q1.

## Approach

Rewritten after Q1 b; the first draft parsed kaikki at build.

- **Generator.** Our own pt rules generate the forms of a base word from the classes of its senses
  (lexfile class, not the lemma's majority part of speech, since *ser* and *saber* are nouns as
  lemmas): a noun's plural; an adjective's feminine and plurals; a verb's finite forms, personal
  infinitive, gerund and participles, from the regular -ar, -er and -ir paradigms with their
  spelling changes (*ficar*, *fiquei*; *conhecer*, *conheço*), stem changes of the -ir verbs
  (*sentir*, *sinto*), and a written table of the irregular verbs and their compounds (*ser*,
  *ter*, *manter*, *pôr*, *propor*). Each form carries its tags (person, number, tense, mood,
  gender). Generating from the base, rather than guessing the base of a form, means a wrong guess
  is mostly a form `wordfreq` does not know, which the floor drops; it can still land on a real
  word of another meaning (a regular form of a rare verb that spells a common noun), which the
  measure against kaikki finds.
- **Analysis.** Inverting the generated forms gives each frequent form its readings; Q4 a picks one
  base. An adjective that is the feminine of another adjective base gives way to it (*novas* of
  *novo*), and a verb gives way to its own participle used as a word (*estados* of *estado*,
  *comidas* of *comida*).
- **Measure.** kaikki stays in the scratchpad as the oracle: the model's base and tags are compared
  with kaikki's on every model form, and with the 421 reviewed form words.
- **Build stage.** `apply_inflections`, right after the sense additions and before `enrich`: for
  each generated form that the build lacks, above the zipf floor (Q3), not a closed-class word,
  create the lemma (part of speech from the form's class) and copy the picked base's senses of
  that class onto it, each with the form note.
  After the best-sense pins, a form whose base has a pin takes the pin on the same concept, so the
  form's card is its base's card. A lemma the build already has is left as it is, so every
  reviewed row wins (Q5).
- **Form note.** Written from the tags in the house style of the reviewed rows: `plural of "ano"`,
  `3rd person singular preterite of "ser"`, `feminine singular of "bom"`, `past participle of
  "fazer"`, without the English rendering the reviewed rows add (Q6). A form with several
  readings of one base merges them (`1st person plural present or preterite of "falar"`).
- **Forms out of drills by default** (Q2): `CardQuery.include_forms`.

## Open questions

- Q1: Source and licence. Every usable table is from Wiktionary under CC BY-SA.
  - a. kaikki's form-of facts, used at build from the raw cache; no Wiktionary text is copied
    (the notes are ours), the manifest and `docs/library/lexicon.md` name the source and its
    licence. The corpus's licence posture is noted as "facts from a CC BY-SA source".
  - b. Rules of our own only (endings plus an irregular table), with kaikki used only to measure
    them in the scratchpad, never by the build. Permissive, more code, lower coverage, and every
    wrong base is a wrong card.
  - c. Accept CC BY-SA for the whole corpus, as `05.4_data_quality.md` brainstorm option (b).
  - Recommended: a, because it covers 363 of the 379 reviewed content forms with the right base,
    the corpus already treats edges as facts, and only our own text is shipped.
  - ANS: b (user, 2026-11-11): rules of our own only; kaikki is used only in the scratchpad, to
    measure the rules. Supersedes the kaikki parts of "Proposed approach" (rewritten below).
- Q2: Should model forms be drill cards? Today a form with a reviewed row is a card like any word
  (*anos* in pair matching shows "year"). At zipf 3.0 the model adds about 10,800 pt lemmas to the
  about 46,000, and each would be a card.
  - a. Cards, like the reviewed forms.
  - b. Out of card queries by default: `CardQuery` gains `include_forms: bool = False`, which
    leaves out every lemma whose card has a form note, the reviewed forms included (one rule);
    `lemma_card` by id still serves them, so a client looking up *foi* gets *ser*'s meaning with
    the note.
  - c. Out by default, but the reviewed forms stay in.
  - Recommended: b, as the function words in `16_card_pos_filter`, because a drill of the base word
    already teaches the meaning, a pool one fifth inflected forms changes every drill, and the
    reviewed forms are no different in kind. It changes the frozen surface (a new field and a new
    default), so it needs a CHANGELOG line and a release.
  - ANS: b (user, 2026-11-11).
- Q3: Zipf floor of the forms the model adds.
  - a. 4.0: 2,126 forms.
  - b. 3.5: 5,381.
  - c. 3.0: 10,834.
  - Recommended: c, because with Q2 b the forms cost only size, and a client looking up a form a
    learner meets (zipf 3 is about once per million words) should find it; with Q2 a, b instead.
  - ANS: c (user, 2026-11-11). The 10,834 were counted with kaikki as the analyser; the rules give
    their own count, which phase 1 reports.
- Q4: A form with several bases (370 at zipf 3.0).
  - a. One base: drop a reading tagged second person or pluperfect when the form has another
    reading (*formas* keeps *forma*, *vira* keeps *virar*), then keep the base with the highest
    zipf (*foi*: *ser*); the others are counted and listed in the phase report.
  - b. Every base: the form carries the senses of each, and the card is whichever sense ranks
    first (the frequency tie means commonness decides, so *foi* could show "go" or "be" by chance).
  - Recommended: a, because the card must be predictable, and b's search benefit (*foi* finds
    *ir*) has no endpoint that uses it today; phase 1 measures the rule on the reviewed forms.
  - ANS: a (user, 2026-11-11, "take all as recommended").
- Q5: The reviewed form rows of `14_number_modal_words` phases 5 and 7.
  - a. Kept: the model skips any lemma the build already has, so a reviewed row always wins, and
    a later review fixes a model form by writing a row.
  - b. Replaced: retract the rows the model reproduces.
  - Recommended: a, because the rows carry choices the model cannot make (*todos* "all", *pais*
    "parents") and an English rendering, and keeping them costs nothing.
  - ANS: a (user, 2026-11-11).
- Q6: Form note text.
  - a. The grammatical label only: `3rd person plural present of "ser"`.
  - b. The label plus an English rendering made from the base card's first English translation
    (`: they are`), which needs English inflection rules and goes wrong on irregular verbs.
  - Recommended: a, because the card already shows the base's translations, and a wrong English
    rendering is worse than none.
  - ANS: a (user, 2026-11-11).
- Q7: Forms that are also a word of their own in kaikki (522 at zipf 3.0: *velha* "wife",
  *imagina* "no problem", *frito* "screwed").
  - a. Added as forms anyway, and listed in the phase report for a later review.
  - b. Left out until reviewed.
  - Recommended: a, because the form reading is right for nearly all of them, the own sense is
    mostly a colloquial extra, and the list makes them reviewable.
  - ANS: a (user, 2026-11-11). With Q1 b the build cannot tell an own word; phase 2 lists the
    model forms kaikki gives a sense of their own, from the scratchpad copy.
- Q8: Where the form table lives. kaikki serves only its latest extract, updated about weekly,
  with no dated archive (checked on its raw-data page), while OMW is pinned by version (`1.4`).
  - a. The acquire stage downloads the latest extract (582MB, about 3 minutes) into the gitignored
    raw cache and records its extraction date in `_build.json`; the build parses it. A later
    rebuild can get a different table.
  - b. A derived table (form, base, class, tags, for forms of zipf 2.5 and up; a few MB) committed
    under `data/sources/kaikki_forms/pt.jsonl` through LFS, with the extract's date in a header
    row, regenerated on purpose by a script; the build reads only that.
  - Recommended: b, because a rebuild must reproduce the corpus, and a weekly-changing download
    cannot; the committed table is also what a diff shows when it is refreshed.
  - ANS: b (user, 2026-11-11), made moot by Q1 b: the rules are code, so there is no derived
    table to commit. The irregular verbs are a table in that code, written by us.

### Raised in phase 2

- Q9: Card translations list the inflected forms. `lemma_store._card_translations` takes every
  lemma with a sense on the card's concept, so on v0.6.0 the en card "year" shows pt
  `['anos', 'ano']` and "be" shows 26 pt words with *ser* 13th (the reviewed forms of
  `14_number_modal_words`). The model adds a form to most pt concepts, so most cards would list
  forms. The same holds for the pt card's own-language synonyms, `lemmas_for_concept` and the
  `require_translation` filter.
  - a. A sense with a form note is never a translation, a synonym or a concept member in those
    reads; `lemma_card` by id and the form's own card are unchanged. Done in phase 3 with the
    card filter.
  - b. Only the translations of a card; the concept reads keep the forms.
  - Recommended: a, because a form is not another word for the concept anywhere a list of words is
    shown, and it fixes the shipped defect too.
  - ANS: a (user, 2026-11-11). Folded into phase 3.
