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

## `lang_tools.lexicon` needs fastapi-tools to import

`lemma_store` imports `get_lang_tools_params`, which imports `WebappParams`, which imports
`fastapi_tools`; but fastapi-tools is only in the `webapp` extra.
Measured on a clean venv with `lang-tools @ v0.2.0`: `from lang_tools.lexicon import LemmaCard`
raises `ModuleNotFoundError: fastapi_tools`, and works with `lang-tools[webapp]`.
lang-tutor never hits it because `make sync` installs every extra.
Fix candidates: a lazy webapp-params import, or fastapi-tools as a base dependency;
either needs a patch release and a pin bump.
Found in the `09_concept_model` backlog.

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

## Junk best senses on common pt forms

Frequent words whose best sense was a rare homograph, met on the first cards.
Checked on 8010 on 2026-11-12: *seja*, *são* and *Brasil* now show the right card,
but *é* still shows "the 5th letter of the Roman alphabet".
Fix candidates: a curated pin for the remaining top forms, or a rule that a sense with no
frequency data cannot become the best sense of a common lemma.
Found in the `09_concept_model` backlog.
