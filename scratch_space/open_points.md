# Open points

Known problems with no plan folder yet, one section each.
To work on one, open a numbered folder for it, start its `00_start.md` from the section,
and remove the section here.
A new point gets a section: what is wrong, how big, and where it was found.
Problems whose fix is lang-tutor code are in lang-tutor's `scratch_space/open_points.md`.

## pt *pêlo* / *pelo* homograph

The corpus keeps the old spelling *pêlo* "hair", since respelt it would be the closed-class
*pelo* "by the".
Two reviewed look-alike rows on *pelos* (it *pelo* "hair", *peloso*) were reviewed for "hairs",
which this corpus spells *pêlos*, so they now sit on the contraction "by the".
Found in `14_number_modal_words/07_closed_class_concepts.md` and `06_spelling.md`;
the spelling rule is in `docs/library/lexicon.md`.

## Doubtful base picks for three pt forms

From a read of 100 of a 500 sample of the inflected forms the build adds:
*virei* (the future of *vir*; in speech mostly *virar* "I turned"),
*obvio* (a misspelling of *óbvio*, read as *obviar*),
*rebelo* (mostly a name).
Found in `15_inflection_model/02_build_stage.md`.

## Wrong glosses inherited from the base's card

A form shows its base's card by design, so a wrong card on the base shows on its forms too.
Three seen in the same read: *gorduras* "soil, dirt", *troncos* "belly", *pintadas* "paved".
A card review of the bases fixes both.
Found in `15_inflection_model/02_build_stage.md`.

## pt forms that are also English words or names

Kept on purpose, with no filter, since forms are out of drills by default:
183 forms as frequent in English as in Portuguese (*to*, *for*, *some*, *times*, *classes*),
most of them real pt forms, with *to* and *does* noise;
140 forms that kaikki also lists as names (*gomes*, *castro*, *domingos*, *irão*), most of them
real forms too.
Worth a look only if forms come back into drills or word lists.
Found in `15_inflection_model/01_form_table.md`.

## Mapping new lemmas into the corpus

The phase-8 maintenance loop (worklist, proposer, reviewed JSONL, curated build input) was
meant to also map new lemmas: a word that is not in OMW (a learner's lookup, a frequency-list
form, an LLM-generated lemma) gets proposed concept links, reviewed before the build applies
them.
Deferred because nothing feeds new lemmas in yet, so there is no worklist to run;
pick it up when a source appears.
It would also cover the OMW coverage holes the look-alike measurements hit: en *parents*,
es *embarazada* and *constipado*, and pt *eventualmente* are absent.
Found in `09_concept_model/08_maintenance.md`, Decisions, item 1.

## Merge on re-ingestion

The corpus is built from pinned sources plus the committed curated inputs under
`data/curated/`, so a rebuild reproduces curated state.
What does not exist is a merge for when an upstream source changes, such as a new OMW
release or re-sourcing pt from upstream own-pt for licensing: it would diff the new machine
output against the old baseline and re-check the curated rows that went stale.
The per-row `source` tag and the build manifest were kept as the seam for it.
Found in `09_concept_model/05_ingestion.md`, "Deferred: re-ingestion merge".

## `derivation` and `pertainym` relations

OMW-en carries 74,708 derivation and 8,023 pertainym links (*happy* -> *happiness*,
*atomic* -> *atom*).
The relations phase left them out: they are English-only, sense-level morphology, and nothing
consumed them.
They would matter for a word-family feature ("words built from *feliz*"), or as a signal for
telling a derivational relative from a false friend.
Found in `09_concept_model/07_relations.md`, Decisions, item 3, and Out of scope.

## More example sentences for pt, es, fr

OMW has example sentences for en (about 33k concepts) and it (about 1.4k) only.
10 hand-written rows in `data/curated/example_sentences.jsonl` proved the path, with
`CardQuery.example_mentions_lemma` keeping each one to the lemma it uses;
sentence reconstruction works, but has only 3 or 4 sentences per language.
Two ways to scale it:
an LLM job on the maintenance loop (an A1 to B1 worklist, one sentence per lemma,
sample-measured and approved before a paid run),
or Tatoeba (CC-BY, already staged), the sourced alternative.
Found in `09_concept_model/09_sample_and_consumer.md`, Q1.
lang-tutor has a written plan for it, deferred on 2026-11-03:
its `scratch_space/03_ui_followups/04_sentences.md`.

## pt glosses for the concepts own-pt added

With pt from OpenWordnet-PT, pt words are linked to 8,868 concepts that have no pt gloss
(of 52,706 pt concepts): the gloss backfill covered the concepts omw-pt had.
Cards show the en gloss by default, so a learner sees the gap only with a pt gloss language.
The fix is a run of the existing gloss backfill job over those concepts; the 2026-10 run wrote
174,315 glosses for about $1.87, so this is on the order of $0.10, to be measured on a sample.
Found in `18_licensing/01_own_pt.md`, parked by `18_licensing/00_start.md` Q12.

## Plan references in `src/`

`src/` holds about 165 "phase N" mentions in 44 files (docstrings, comments, a log message),
such as "(phase 7)" or "phase 5.55 Q4". The plan convention keeps plan ids out of code, and
`plans.py check --citations` does not match this form, so they were never flagged.
The fix: point each at the doc whose topic it is, or drop it, file by file; and teach the
check the "phase N" form so new ones are caught.
Found in `18_licensing/02_license_files.md`, parked by `18_licensing/00_start.md` Q15.

## it cognate missing from the card's meaning

A card lists its look-alikes, and an it cognate of the pt word is often not a word of the
card's meaning: pt *carreira* lists it *carriera* as a cognate, but the meaning "the
particular occupation for which you are trained" has only *vocazione*, so *carriera* is never
offered as a translation. Measured on the 0.9.0 build (2026-11-17): of the 19,599 pt cards
acerta draws, 2,438 have an it cognate of the same part of speech, and for 1,350 of them the
cognate has no sense on the card's meaning. Some are right, the cognate meaning something
else (*perversão* / *perversità*); some are gaps (*época* / *epoca*, *operar* / *operare*,
*restaurar* / *restaurare*, *maestria* / *maestria*).
The fix is a review that adds the real gaps through `sense_additions.jsonl`, with its own
rulebook. Left out of `22_meaning_members`, which only removes and reorders words.

## Card meanings with one pt word

The meaning review of `22_meaning_members` reads the card meanings with two pt words or more
(7,743), where a wrong word is one word of a list. The other 7,512 card meanings have one pt
word, the card itself, so a wrong word there is a wrong card: pt *escotilha* (a ship's hatch)
is the only pt word of "the production of young from an egg" (en *hatching*, *hatch*), found
by that folder's lead smoke batch. The card-sense review asks whether a card's meaning is
right with the card's other senses in view, and has covered the most frequent cards; the rest
of the 7,512 have had no review. The fix is that review's drops and pins, extended down the
card list.

## Unreviewed card meanings

`22_meaning_members` reviewed the pt words of 1,705 of the 7,743 card meanings with two pt
words or more (the first by concept key, a fair sample), and stopped there on cost: about 2.2
session points per batch of 100 meanings, so the other 6,038 would take about 61 batches,
135 session and 19 weekly points. In the reviewed set about 2 in 100 words were dropped (a
word naming something else, a definition, a misspelled or pre-1990 duplicate) and 1 in 100
became a form of another word (*canais* of *canal*). The harness is ready: `meaning_review_cli
worklist`, then batches from `w0019`, under `docs/guides/meaning_review.md`. A cheaper scope
is the meanings of A1 to B2 cards only.

## Translations led by a generic en verb

A card pairs the first en word of its meaning, and a meaning's words are ordered by frequency,
so a generic verb that WordNet lists in a narrow meaning leads it: pt *experimentar* ("go
through mental or physical states") pairs with *have*, not *experience*; *executar* with *do*,
not *perform*; *especificar* with *set*, not *specify*; *instituir* with *make*, not
*establish*. On the 0.10.1 build, 77 drill cards lead with one of *have*, *get*, *make*,
*take*, *give*, *go*, *do*, *put*, *set*, *come*, *run*, *let*, *keep*, *hold*, *turn*,
*bring*, with another en word behind it; some are right (*pôr* - *put*, *obter* - *get*).
Same kind as the -ing leads `22_meaning_members` fixed, and the same fix: the meaning
review's lead batches with these verbs added to `build_lead_worklist`'s test, about one
batch. Found from lang-tutor's 0.10.1 check (lang-tutor `scratch_space/05_lang_tools_0101`).

## Plain cognates the look-alike generator misses

The look-alike candidates are found by spelling only, tuned for traps, and many plain cognates
of a card's own translation are never candidates, so they carry no `cognate` edge:
pt *dezembro* / en *December*, *acesso* / *access*, *coragem* / *courage*, *semana* / it
*settimana*, *saúde* / *salute*, *pouco* / *poco*, *ouro* / *oro*.
Causes seen in `lookalikes.find_candidates` and `cognate_key`: the block join compares only keys
that share their first two letters, and en hard *c* becomes *k*, so *aces* and *akces* never
meet; *coragem* / *courage* (0.57) and *saúde* / *salute* (0.60) are under the 0.65 threshold;
*acesso* got *ace*, *cease*, *aceto* instead, all rejected.
How big: in acerta's shipped asset (lang-tools `v0.10.1`), an 8-pair C2 round holds about 2.3 en
and 2.9 it pairs whose pt word and right word have a folded spelling ratio of 0.7 or more, and
2.0 en / 2.4 it of those have no look-alike at all.
A likely fix: a pt word and a translation that share the word's best concept and look alike are
a cognate by construction, so they could become edges with no review.
acerta works around it on its side with a spelling check on the shown pair
(acerta-word-drills `plans/03_false_friend_rounds`).
Found on 2026-11-23 from the user's play at C2.

## Look-alikes whose main meaning is a rare sense

The shared-meaning review labelled 15 false-friend pairs `w`: the look-alike's best sense, which
`LookalikeHint.means` shows, is not what it mainly means (it *terza* as a baseball position, not
"third"; it *mensa* as a recreation room, not a canteen; en *post* as "publicize with a poster").
The list is the `w` rows of `data/curated/shared_meaning_log.jsonl`; a fix is a best-sense pin,
or a sense addition where WordNet lacks the meaning.
Found in `24_partial_false_friend_meanings/05_rebuild.md`.

## Full false friends that share the main meaning

The same review labelled 24 `full` pairs `s`: the pt word is used for the look-alike's main
meaning (pt *sorte* "a kind", as in *toda sorte de*; pt *cartão* "cardboard" in Portugal), which
the look-alike rulebook says a full pair never is.
Each may be `partial`, or the `s` may be a stretch (pt *divertido* ~ en *diverted*).
The list is the `s` rows of `full` kind in `data/curated/shared_meaning_log.jsonl`; a fix is a
look-alike re-check of those pairs.
Found in `24_partial_false_friend_meanings/05_rebuild.md`.

## A wrong learner note on pt *bruto* / it *bruto*

The edge's note says it *bruto* means ugly; it mainly means brute or rough, and "ugly" is
*brutto*. Reported by the shared-meaning review batch `p0006`; a fix is a corrected row in
`data/curated/lookalikes.jsonl`.
