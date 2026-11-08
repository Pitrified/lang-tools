---
status: done
priority: 0
description: |
  Add the concept links the corpus is missing for frequent words, so their cards teach the
  everyday meaning (pt *sim* "yes", *vinte* "twenty", *aí* "there"), and bring back the frequent
  words the card review removed. A new curated input, applied at build like the drops and pins.
comment: |
  Spun off on 2026-11-05 from scratch_space/12_card_senses (00_start.md Q8), whose pt review
  could only pick among the senses that exist. Widened on 2026-11-06 to fix the 16 pt cards
  still wrong after that review (lang-tutor 03_ui_followups/03_first_cards.md), all in
  lang-tools; lang-tutor only bumps its pin.
---

# Missing senses

## Origin

The card-sense review in [`12_card_senses`](../12_card_senses/00_start.md) keeps, pins or drops
the senses a word is linked to; it cannot add one.
Its re-list of the pt top 500 cards left 16 doubtful cards
([`04_review_run.md`](../12_card_senses/04_review_run.md)), and its drops removed whole lemmas
whose every link was wrong.
Adding links is a different job (a new curated input, not a review label), so it gets its own
folder.

On 2026-11-06 the user asked to fix those 16 cards here, in lang-tools, in the same pass;
lang-tutor gets no workaround, only the pin bump of the release.

## Analysis (2026-11-06)

### The 16 doubtful pt cards, read against the corpus

Every one is fixed by the same move: link the word to the concept it is missing, then pin it.
None needs a change to the card's translation rule, which was the first guess for three of them.

| Group | Words | What the corpus has | Target concept |
| -- | -- | -- | -- |
| No right sense | *sim*, *além*, *última*, *seis*, *partes*, *nomes*, *irmãos* | *sim* only "yea" ("not only so, but"); *seis* only the playing card | "yes", "beyond", "last", "six" (the number), "part", "name", "brother" |
| Odd translation | *aí*, *lá*, *primeira* | *aí* and *lá* only "yonder" (members *yon*, *yonder*); *primeira* only "first in rank" (*prime*, *premier*) | "there", "first" |
| Verb-form homograph | *são*, *vão*, *passa*, *leva*, *precisa*, *preciso* | the adjective or noun only (*são* "healthy", *vão* "vain") | the verb's concept ("be", "go", ...), see Q1 |
| Capitalised twin | *natal*, *índia* | the meaning is on another lemma: "Christmas" on *Natal*, "India" on *Índia* | see Q2 |

The targets checked so far exist as concepts: "yes", "twenty", "six", "headquarters", "beyond",
"brother", "direction", "Christmas", "India".
Two of them carry a wrong pt member that a drop can clear while we are there: "yes" has the
English word *yes* as a pt member, and "six" has only *6*.

### Lemmas the card review removed

The review dropped 106 senses and with them 60 pt lemmas whose every link was wrong (61, less
*moderna*, restored in `12_card_senses` phase 5). A new link brings a lemma back, since its id
comes from its text and language. They sort roughly into:

- everyday words worth a card: *vinte*, *cura*, *campeonato*, *destaque*, *terras*, *minutos*,
  *regras*, *jogos*, *cartas*, *ferramentas*, *interesses*, *órgãos*, *trabalhos*,
  *universidades*, *alerta*, *terça*, ...;
- verb forms: *deve*, *fez*, *faça*, *possa*, *veio*, *vinha*, *penso*, *falo*, *amo*, *ama*,
  *pega*, *percebe*, *pertence*, *quebra*, *cria*, *ido*, *feita*, *recebido*, *morrendo*,
  *haver*, ... (Q1 decides them as a group);
- names written in lowercase: *brasil*, *angola*, *cuba*, *pernambuco*, *paul*, *pereira* (Q2);
- English words or fragments: *go*, *center*, *pop*, *ai*, *mi* (stay out).

Bringing one back also re-attaches its look-alike rows: 28 of the 34 rows the 2026-11-06
build skipped as stale sit on these lemmas. The other 6 sit on closed-class words (*como*,
*quando*, *qual*, *durante*, *pelos*), dropped by the build's closed-class rule on purpose,
and are out of scope.

### The mechanism

- A new curated input, `data/curated/sense_additions.jsonl`: one row per (lemma, concept key)
  with the word, its language, the reason, and `add` (a later `add: false` row retracts it);
  latest row wins per key, as for drops and pins.
- A build stage right after the drops, so an addition wins over a drop of the same link and
  everything downstream (frequency, CEFR, topics, look-alikes, pins) sees the new sense. It
  creates the lemma when the build lacks it, the way the OMW source does (`Lemma(text,
  language, part_of_speech, sources)`), and counts a row whose concept is gone as stale.
- The review harness of `12_card_senses` (`sense_review`), extended rather than copied: a new
  label action `a<concept key>` adds a link (and pins it), with an optional form note (Q7);
  the worklist also serves the removed lemmas, which have no card; a `concepts` command looks up
  concept keys by English word for the reviewing agent; `add` joins `restore` and `pin` as a
  hand correction. Rules in `docs/guides/sense_review.md`, a how-to for other languages in
  `docs/guides/` (Q5).
- Reviewers: one agent per batch with hidden gold, and a measured second review (Q8).

### Measurement

The user's rule for this folder (2026-11-06): a decision rests on at least 500 corpus items,
chosen for the decision rather than at random; 50 is too few.
The counts above come from reading the pt top 500 once, so the plan measures again before and
after, on the pt top 1,000 single-word cards by frequency (the set `12_card_senses` reviewed,
and the cards a learner meets first):

- the phase 2 review covers all 1,000 cards and the 60 removed lemmas; its labels are the
  before table (a `k` is right; an `a`, `p`, `d` or `x` and its reason name the cause), and the
  causes are tallied from the reasons rather than from a list fixed up front (Q2 note);
- a second blind review of 500 targeted items gives the same-rules agreement (Q8);
- phase 3 has one more agent review re-read the same 1,000 cards after the rebuild, with the
  same rules, for the after table.

## Open questions

- Q1: Verb-form homographs and the verb forms the review removed (*são*, *vão*, *fez*, *deve*,
  *possa*, ...). The corpus has no inflected-form model: a form can only be linked to the
  verb's concept, so the *são* card would teach "be" with the gloss of "be", not "are".
  - a. Link each form to its verb's concept and pin it, for the forms in the pt top 1,000.
  - b. Link only the six homograph cards of the top 500; leave the removed forms out.
  - c. Leave verb forms alone: the homographs keep their adjective or noun card.
  - Recommended: a, because the frequent reading of these words is the verb, and a learner who
    taps *são* expects "be" rather than "healthy". The row count is unknown until phase 1
    counts the verb forms in the top 1,000; revisit this answer if it is large.
  - ANS: a, and both (user, 2026-11-06): link the form to its verb's concept, and also tell
    the learner which form it is (*são* is the plural, "they are"). The corpus has no
    inflection model, so the form note needs a home: raised as Q7.
- Q2: Capitalised twins and lowercase names. Cards are lowercase single words only, so *Natal*
  "Christmas", *Índia* "India" and *Brasil* never become cards; lowercase *natal* ("native,
  of birth") and *índia* ("an Indigenous woman") are real words with real meanings.
  - a. Leave proper nouns out of the drill: *natal* and *índia* keep their lowercase meaning
    (pinned to the clearest sense), the lowercase names stay removed, and their look-alike rows
    stay stale.
  - b. Link the lowercase forms to the proper-noun concepts (*natal* "Christmas", *brasil*
    "Brazil"), so the frequent reading is taught.
  - Recommended: a, because the lowercase meanings are correct, and teaching a capitalised
    noun through a lowercase card contradicts the single-word filter.
  - ANS: a, use capitalisation (user, 2026-11-06): proper nouns are capitalised lemmas and
    never cards. The user expects some proper nouns to sit in the corpus in lowercase from
    poor source data (*brasil*, *angola*, *cuba*, *pernambuco*): the review finds them, drops
    the lowercase lemma's links, and adds the link on the capitalised form when that form is
    missing.
  - Note (user, 2026-11-06): the lowercase proper nouns are a guess, not a measured class, and
    there may be other problems. The rulebook does not enumerate guessed classes: a wrong card
    the rules do not name gets a free reason, and phase 2 tallies the causes from the 1,060
    labels before any fix is generalised.
- Q3: Who proposes the links. About 16 cards plus up to 60 removed lemmas.
  - a. The assistant writes them by hand with the `concepts` lookup, as a list in a side file,
    which the user reads before `add` writes them.
  - b. An agent batch with a rulebook section in `docs/guides/sense_review.md`, like the
    review.
  - Recommended: a, because it is under a hundred rows of plain lookups, and a rulebook pays off
    only when the set is large or recurs.
  - ANS: b, agents on top of agents (user, 2026-11-06; the user does not read Portuguese):
    two independent agent reviews of every item, a third agent settles the disagreements,
    and the user reads only the numbers and the residue. Rules in a rulebook, so the pass
    is repeatable.
  - Reopened (user, 2026-11-06): the phrase was sarcastic; the user asked whether the look-alike
    setup (one agent per batch, hidden gold, rechecks) is enough. Assessed and re-asked as Q8.
- Q4: The wrong pt members seen on target concepts (*yes* on "yes", *6* on "six"), and any met
  later in this pass.
  - a. Drop them in the same pass through `member_form_drops.jsonl` (an existing input).
  - b. Leave them; out of scope.
  - Recommended: a, because a link to "yes" should not bring the English word *yes* with it as
    a pt translation, and the drop costs one row each.
  - ANS: a (user, 2026-11-06): drop them and clean up the wrong pt members met in the pass.
- Q5: es and fr, whose cards were never reviewed (fr *comment* "yak", *un* "two", es *china*
  "pebble").
  - a. Out of scope: pt only, as in `12_card_senses`.
  - b. In scope for the same kind of fix.
  - Recommended: a, because they need the review first (to drop the wrong links), which is its
    own pass; the mechanism built here serves them later.
  - ANS: a (user, 2026-11-06): es and fr out of scope, with a how-to guide in `docs/guides/`
    so the pass can be re-run on another language.
- Q6: The release. A new curated input and two commands are additions to the public tooling.
  - a. v0.4.0, then the lang-tutor pin bump (no lang-tutor code).
  - b. v0.3.1.
  - Recommended: a, by the semver rule the changelog follows (new features, nothing breaking).
  - ANS: a (user, 2026-11-06): v0.4.0.
- Q7: Where the form note lives (Q1: *são* teaches "be" and says it is the plural, "they are").
  It belongs to the sense, not the lemma: *são* the adjective "healthy" has no form note.
  - a. An optional `form_note` on `Sense`, written by the addition row (for example
    `present, 3rd person plural of "ser": they are`), carried to `LemmaCard.form_note`. An
    addition to the frozen API (v0.4.0); lang-tutor shows it once its card views read it.
  - b. Put it in the card's gloss through a gloss override. No model change, but the gloss is
    per concept, so every pt card on "be" would say "plural".
  - c. Drop the note: the card teaches "be" only.
  - Recommended: a, because it is the only place that is per sense; showing it in lang-tutor is
    a small view change that would come with the pin bump, and needs your go-ahead there.
  - ANS: a (user, 2026-11-06). lang-tutor is never a blocker to a lang-tools change.
- Q8: Reviewer setup (reopens Q3). Evidence from the logs, 2026-11-06:
  - look-alikes: 93 single-agent batches, 16,968 pairs, hidden gold 424/465 (91%), but `r0011`
    disputed 25% of the hand-written gold traps it re-checked, so gold is a noisy reference;
  - 1,583 pairs were reviewed twice and 377 (24%) changed kind, every one after a rule change,
    so rule changes and reviewer noise cannot be told apart; the biggest moves follow rules
    (unrelated to cognate 127, full to unrelated 109);
  - card senses: 1,000 cards, gold 9/9 (too few to mean anything); a read of the top 500 found
    one plain reviewer miss (*copa*).
  The repeat passes so far came from rule changes, which more reviewers would not have avoided,
  and the number that would justify a second reviewer, same-rules agreement, was never
  measured.
  - a. One agent per batch, as for the look-alikes, plus one measurement: a second blind agent
    on 500 targeted items (every item the first pass changes, filled with kept items), under the
    same rules. 90% or more agreement on the changes keeps single passes, here and for
    look-alike tiers C and D; less, and the disagreements show which rule to fix.
  - b. Two blind agents on every item and an arbiter on the disagreements.
  - c. One agent per batch, no measurement.
  - Recommended: a, because it puts a number on the question for about half a round, and a
    clearer rule is cheaper than doubling every later pass.
  - ANS: a (user, 2026-11-06). The user sees the review method itself as worth an investment:
    meta-experiments to tune it (what a second reviewer catches, which rules disagree, how
    good the gold is) are welcome. The phase 2 measurement is the first one; further ones are
    designed from its numbers, and go to a sibling folder if they outgrow this one.
- Q9: The rulebook contradicts itself on a verb form that is also an everyday noun. Its older
  homograph example says pt *era* keeps and pins the noun "era, age" (and the gold says so), while
  the form rule added for Q1 links an inflected form to its verb with a form note (*são* is "be",
  "they are", and "healthy" stays as a later sense). The `m0004` reviewer applied the form rule to
  *era* ("be", "I/he/she was") and was scored a gold miss. The corpus still pins the noun (gold
  labels are not applied). It touches every verb form with an everyday homograph (*era*, *são*,
  *vão*, *meia*, *levado*, *juro*).
  - a. The frequent reading wins: the verb with its form note is the card, and the noun stays as a
    later sense. Update the rulebook example and the *era* gold; re-pin *era*.
  - b. The noun wins when it is in ordinary use: keep *era* on the noun, and re-check the forms the
    first review moved to the verb over an everyday homograph.
  - Recommended: a, because it is what Q1 asked for (a learner meets *era* as "was" far more than
    as "age"), and the reviewers already applied it everywhere but the gold. The look-alike label
    of pt *era* / en *era* stays `partial`, which suits either card. The rule is changed after the
    second review, so both reviews run under the same rulebook.
  - ANS: a (user, 2026-11-06). Applied after the second review (`n0001` to `n0003`), which
    runs under the unchanged rulebook.
- Q10: The second review (`n0001` to `n0003`, 500 items, same rulebook) agrees with the first on
  458 cards (92%) and 447 outcomes (89%), but on only 108 of the 157 items the first review
  changed (69%), below the 90% bar. The 53 disagreements fall in three groups:
  - 28 are the threshold for a near miss: sense 1 is a narrow or neighbouring reading of the
    everyday meaning, and one reviewer added the everyday concept while the other kept the card
    (*arquivos* "archives" for "files", *câmeras* "tv camera", *nenhum* "neither" for "no",
    *sentir* "perceive" for "feel", *entretanto* "meanwhile" for the Brazilian "however",
    *antiga* "ancient" for "old"; the reverse once, *fato*). Six of them are Q9's case, an
    everyday homograph against a frequent form (*meia*, *juro*, *sede*, *seguros*, *chamado*,
    *privada*). The rulebook pulls both ways: "a narrow sense of a broad meaning is not wrong"
    against "do not pin a near miss", and `k` asks for "the best one to teach first". On a
    read of the reasons the first review's call is the better card in most of them.
  - 14 add the same meaning through a different WordNet twin (*seis* "six" as a quantity or as
    the number, *obrigado* "thanks" twice, *fala*/*falo* "express in speech" or "use
    language", *cria*/*criada* split the two "create" concepts the other way round). The card
    reads the same; the rulebook gives no tie-break, and `concepts` shows neither the
    commonness nor an order.
  - 11 reach the same card and differ only on dropping a second, wrong sense (*além* "yonder",
    *novamente* "newly", *ponto* "skull joint"); the first review dropped more.
  - a. Fix the rules, then serve the 53 again as a re-check (`m0006`, under the new rulebook,
    so its rows win), and let phase 3's second review of the 1,000 measure agreement under the
    new rules. The fixes: `k` means sense 1 is the everyday meaning itself, and a narrow or
    neighbouring sense 1 takes `aKEY` with the everyday concept, the narrow sense staying later
    (examples from the list above); Q9's "the frequent reading wins"; for twin concepts, the
    one the base word's card uses, else the most common, with `concepts` printing the
    commonness and sorting by it; and `agreement` counting a twin with the same first English
    translation as the same card, reported apart.
  - b. Accept the first review as it stands, apply only Q9, and carry the measured 69% into
    the guide as the known spread.
  - Recommended: a, because the near-miss split is a rule the next language will hit as well,
    and phase 3 already pays for the second review that checks the fix. Cost: about 5% of the
    5-hour meter for `m0006`, and a small tool change for `concepts` and `agreement`.
  - ANS: a (user, 2026-11-06).
- Q11: A re-check serves an item as the worklist recorded it, before any review, so its
  reviewer never sees the earlier review's additions and drops, and a `k` leaves them in place
  (only the pin is released). In `m0006` that is 3 items: *seguros* keeps the first review's
  "safe" next to "insurance", *marina* stays without its dock sense, and *eis* keeps "here"
  (which the `m0006` reviewer, finding no "here is" concept, would likely have taken). Phase 3's
  second review is not touched (it writes no curated row), but every later re-check is.
  - a. Serve a re-check item as the corpus stands after the curated rows: its senses from the
    rebuilt store, the earlier additions among them, and a note of the senses dropped, so a `k`
    endorses what is there and a fix is an explicit `d` or a restore. Phase 3 rebuilds first,
    so this lands before the next re-check.
  - b. Keep serving the snapshot, and document that a re-check only adds.
  - Recommended: a, because a re-check should judge the card a learner sees; the 3 items stand
    as they are meanwhile (each is defensible).
  - ANS: a (user, 2026-11-06).
    Correction (2026-11-06, on reading `_write_items`): the premise was wrong. A re-check is
    served from the built corpus, not from the worklist; the corpus had not been rebuilt since
    the first review, and curated rows only take effect at build. So a takes no code: rebuild
    before a re-check (the guide and the skill say so), and the reviewer sees the earlier
    additions as senses. Dropped links stay hidden, which is right for a wrong link; a dropped
    link that is right after all is a hand `restore`.
