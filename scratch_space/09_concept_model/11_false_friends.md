---
status: planned
---

# Phase 11 - false friends

> Plan of record (2026-10-22): the brainstorm below with its measurements, plus the
> Decisions section. It runs **before**
> phase 10 (licensing): any new source it pulls in (a pronunciation tool or lexicon) then
> gets license-checked with the rest.

## Goal

Fill the empty `false_friends` table with look-alike lemma pairs across languages whose
meanings differ. Examples: es *embarazada* (pregnant) / en *embarrassed*, pt *puxar*
(pull) / en *push*, es-pt *aceite* (oil / accepted).

Everything downstream already exists:

- `FalseFriendRelation`, a symmetric lemma-level edge stored once in canonical order.
  It carries `similarity_score` and per-language `explanation_notes`.
- The store lookup `get_false_friends_for_lemma`.
- `GET /api/v1/lemmas/{id}/false-friends`.
- The brainstorm's consumer ideas (`00-concepts-brainstorm.md`, section 4 and "False-friend
  warnings / trap exercises").

What never existed is a way to **find** them. Phase 7 noted that "no source supplies
them", and phase 8 deferred them because "candidate generation needs designing first".
That design is this phase.

## What counts as a false friend

Four kinds of pair turn up among look-alikes. Only the first two are false friends, and
the pipeline has to tell all four apart:

| Kind | Example | Meaning overlap | Ship as |
| --- | --- | --- | --- |
| **Full false friend** | en *exit* / es *éxito* (success), es *polvo* (dust) / pt *polvo* (octopus) | none | false-friend edge |
| **Partial false friend** | en *assist* / pt *assistir* (assist, but mostly watch / attend) | a minor sense only | false-friend edge, the note says which sense |
| **True cognate** | en *conclusion* / pt *conclusão* | the main sense | not a false friend ("free vocabulary", a possible later feature) |
| **Look-alike noise** | en *festival* / pt *feia*, en *cash* / pt *caos* | none, but nobody confuses them | nothing |

The last row is why "similar spelling plus no shared concept" is not a definition.
Unrelated words that happen to be close do not trap a learner. A trap needs both a
strong resemblance (often a shared Latin root) and a meaning that diverged.

## Measurements (2026-10-22, current corpus)

**Learner pool:** single lowercase words, at least 4 letters, best sense B2 or easier.
That gives about 2,500-3,500 lemmas per language.

**Gold check:** 41 classic false-friend pairs, written down from memory across
en-{pt,es,fr,it} and es-pt.

1. **Coverage holes.** 7 of the 41 cannot be found at all because a lemma is missing from
   OMW: en *parents* (plural only), es *embarazada* (only the masculine *embarazado*
   would be), es *constipado*, pt *eventualmente*, es *rato*. A candidate generator
   cannot fix that; new-lemma mapping (backlog) could.
2. **Spelling similarity alone.** Jaro-Winkler at least 0.88 between the folded forms,
   with no shared concept in any sense, gives 2,300-3,800 candidates per language pair.
   A sample is mostly noise:
   - inflections and derivations: *amigo* / *amiga*, *compra* / *comprar*;
   - OMW gaps: cognates that share no concept only because the other wordnet lacks the
     sense, e.g. en *conclusion* / pt *conclusão*;
   - short-word collisions: *cast* / *casa*, *card* / *cara*.

   Real hits in the sample include *express* / *exprès*, *aceite* / *aceito* and
   *punto* / *puto*.
3. **Spelling plus a meaning test.** Of the 33 gold pairs present, **26** are caught
   when the meaning test is "the look-alike is not a translation of the word's *best*
   sense, in either direction". An exact translation match is required; a fuzzy one
   wrongly filed *soap* / *sopa* as a cognate, because *sopa* translates to *soup*. The
   7 misses split into two groups:
   - **spelling diverges**, Jaro-Winkler below 0.85 (5): *push* / *puxar* 0.63,
     *actually* / *atualmente* 0.74, *library* / *livraria* 0.82, *factory* /
     *fattoria* 0.82, *lunch* / *lanche* 0.84;
   - **errors in the source data** (2): OMW-fr lists *librairie* (bookshop) in the
     *library* concept, and OMW-pt maps *assistir*'s most common sense to *assist*.
4. **Precision is the hard part.** That recall-oriented rule still keeps **5,200-8,700**
   candidates per language pair. So the generator gets the recall and something else
   (ranking, then a verifier) has to get the precision.

## Brainstorm

### Is a simple fuzzy distance enough?

No, but it is a necessary first stage. Fuzzy spelling distance is a good **generator**:
cheap, deterministic, and it already catches 26 of 33. It is a bad **classifier**, for
two reasons:

1. **It cannot see meaning.** Most close pairs are cognates or noise, not traps.
2. **It misses the pairs that differ in spelling but not in sound or root.**
   *push* / *puxar*, *factory* / *fattoria* and *actually* / *atualmente* are the
   textbook traps, and all three fail a 0.85 threshold.

Ways to improve the generator, cheapest first:

- **Better spelling metrics than raw Jaro-Winkler.** Jaro-Winkler favours shared
  prefixes, so *festival* / *feia* scores 0.85. Options: normalized Levenshtein with a
  length-ratio guard, or the longest common subsequence ratio used in cognate
  detection. Plus a minimum similarity that rises as words get shorter, since short
  collisions are noise.
- **A cognate key.** Rewrite each form with known cross-language spelling
  correspondences before comparing, for example:
  - suffixes *-tion* / *-ção* / *-ción* / *-zione*;
  - *ct* -> *t* (pt) and *ct* -> *tt* (it);
  - *ph* -> *f*, *th* -> *t*, *y* -> *i*;
  - *x* / *ch* / *sh* / *sc* collapsed;
  - doubled consonants collapsed;
  - final vowels stripped.

  Then compare the keys. *factory* -> `fatori` and *fattoria* -> `fatori` match,
  *actually* -> `atual` and *atualmente* -> `atual` match, *push* -> `pus` and *puxar*
  -> `pusar` get close. It is deterministic, has no dependencies, and the rule table is
  reviewable. This is the brainstorm's main idea for the five spelling misses.
- **Phonetic distance.** See the next section.

### Do we have IPA for the lemmas?

**No.** OMW 1.4 ships no pronunciations; the 5.4 metadata catalog records them as "not
in `wn` for OMW 1.4 lexicons in practice". Wiktionary's `sounds` (IPA) came with kaikki,
which was dropped in 5.5 for CC-BY-SA, and its raw dump is gone. So IPA would be a new
source. The options:

| Source | Coverage | Kind | License (to verify in phase 10) |
| --- | --- | --- | --- |
| **espeak-ng** | all five languages | rule-based program with dictionaries; good on shallow orthographies (es, it, pt), decent on fr, uneven on en | GPL-3 program; we would only store its output |
| **Epitran** | pt, es, fr, it rule-based; en needs Flite's `lex_lookup` | rule-based Python library | MIT |
| **CMUdict** | en only (~134k words, ARPAbet, maps to IPA) | lexicon | BSD-style |
| **WikiPron / Wiktionary IPA** | all five, curated by people | lexicon scraped from Wiktionary | CC-BY-SA, the license we dropped kaikki over: at most an evaluation reference, never shipped |
| **PanPhon** | any IPA string | articulatory feature vectors plus a feature-weighted edit distance | MIT |

A phonetic channel would be:

1. G2P every learner-pool lemma, about 15k words, which is cheap and offline with
   espeak-ng or Epitran plus CMUdict.
2. Compare the IPA with a feature-weighted edit distance (PanPhon), so /ʃ/ vs /s/
   costs less than /ʃ/ vs /k/.
3. Use that score next to the spelling score.

It catches sound-alikes that spelling hides (*push* /pʊʃ/ vs *puxar* /puˈʃaɾ/) and
matters for listening, where a learner hears a trap rather than reading it.

**Lean:** the cognate key first, phonetics second. Spanish, Italian and Portuguese
spelling is shallow, so spelling plus correspondences already approximates sound. The
one deep orthography is English, which is exactly where G2P is least reliable without a
lexicon. Measure first: if the cognate key catches *push* / *puxar*-type pairs on the
gold set, IPA adds a dependency and a license question for little. If it does not, add
espeak-ng (one tool, all five languages) as a ranking feature.

### The meaning test

"Meanings differ" has to survive the sparse non-English wordnets, where a missing link
looks just like a different meaning. Candidate signals, combinable:

- **(a) No shared concept in any sense.** Too weak alone: OMW gaps make true cognates
  look unrelated.
- **(b) Main-sense test** (measured above). The look-alike is not a translation of the
  word's best sense, in either direction; for two non-English words, compare through
  English. This catches **partial** false friends that share only a minor sense.
- **(c) Concept distance.** Wu-Palmer or path similarity between the two best concepts
  over our own hypernym graph (phase 7, `hypernym` + `instance_hypernym`). It is
  deterministic and free, and separates *soup* vs *soap* (far apart) from *notable* vs
  *notably* (same thing, different part of speech).
- **(d) Gloss similarity.** Embed the two English glosses. This costs money (OpenAI
  embeddings are cheap but are a paid call) or a local model, and adds little over (c)
  plus the verifier.
- **(e) Part-of-speech and derivation guard.** A pair that differs only by inflection or
  part of speech (*compra* / *comprar*, *continue* / *continu*) is a relative, not a
  trap. The `derivation` relations from the backlog would help, but they are
  English-only.

### Verification and notes: the LLM step

Even ranked, thousands of pairs per language pair need a judge, and every edge needs
`explanation_notes` ("es *éxito* means success; the English *exit* is *salida*"). That
fits the phase-8 loop exactly:

1. A worklist of ranked candidates goes to a classifier chain.
2. The chain picks one of the four kinds from the table above and, for false friends,
   writes the note in the learner's language.
3. The output lands in a reviewable JSONL, then in a curated build input
   `data/curated/false_friends.jsonl`, keyed on lemma ids (stable since phase 8 step 9)
   and applied at build (the 5.58 rule).

The prompt is grounded in both lemmas' senses, with glosses and translations, so the
model judges our data rather than its memory. It flags OMW errors like *librairie* as a
side effect.

Cost, rough: for en x {pt, es, fr, it}, the top 1,000-1,500 candidates per pair is about
5k items, roughly 300 tokens each. With a small model on Batch that is well under $1.
**Sample-measured and approved before any paid run**, as always.

### The gold set as the yardstick

Formalize the 41 pairs, extended to about 60-80 covering all ten language pairs, as a
committed, hand-written `false_friends_gold.jsonl` with the kind per pair. Every
generator variant reports **recall on the gold set** and **precision on a hand-labelled
sample** of its own top candidates. Decisions (cognate key vs IPA, thresholds, how many
candidates to send to the LLM) are made on those two numbers.

## Proposed shape (to be confirmed)

1. **Gold set.** About 60-80 hand-written pairs with kinds, plus a scorer.
2. **Deterministic candidates.** Spelling metric plus cognate key, the main-sense meaning
   test (b), the concept-distance rank (c) and the derivation / part-of-speech guard
   (e). Report recall and sampled precision per language pair. No new dependencies.
3. **Phonetic channel, only if step 2 misses the spelling-divergent gold pairs.**
   espeak-ng G2P plus a PanPhon distance as an added ranking feature. License noted for
   phase 10.
4. **LLM verifier plus notes** on the top-N per language pair. A sample run first, then
   cost and quality reported, then approval, then the full run.
5. **Build input and gate.** `data/curated/false_friends.jsonl` is applied at build. Gate
   invariants: both endpoints exist, no self-pairs, canonical order, no duplicate pairs,
   every edge has a note in at least one language.
6. **Surface it**, minimally: the lemma detail page in `lang-tutor` shows the warning,
   and `LemmaCard` or a cards query flag carries it so a pair-matching round can use a
   false friend as a distractor.

## Decisions (settled 2026-10-22)

1. **Languages: en, pt, it**, as three pairs: en-pt, en-it and pt-it. es and fr come
   later, with the same pipeline.
2. **Cognate key first.** The deterministic spelling-correspondence rules go in step 2. The
   IPA channel (espeak-ng plus PanPhon) is added in step 3 only if the gold set shows
   spelling-divergent pairs the key still misses.
3. **`kind` field on `FalseFriendRelation`:** `full` or `partial`, so a drill can pick
   only full traps. This is a small model, codec and schema change, and needs a cache
   version bump.
4. **Keep true cognates.** The verifier labels them anyway. They are stored as a separate
   output for a later "free vocabulary" deck, not as false-friend edges; whether that
   is a `cognates` table or a curated JSONL only is decided in step 4.

## Open questions

- *(settled: language pairs, phonetics, partial false friends, cognates; see
  Decisions.)* Still open: the learner-pool bound (below), and the gold-set size for
  three pairs (about 20-25 per pair).
- **Language pairs (settled: en x pt x it).** en x {pt, es, fr, it} only, which is where a learner whose base
  language is English gets trapped, or all ten pairs (es-pt is rich: *polvo*, *oficina*,
  *aceite*)? Lean: en x 4 first, inter-Romance next.
- **Partial false friends.** Same edge with a note, or a `kind` field on
  `FalseFriendRelation` (full / partial)? A field is a small model change, but lets a
  drill pick only full traps.
- **True cognates.** The verifier labels them for free. Keep them, as a separate
  `cognates` output for a "free vocabulary" deck, or drop them?
- **Phonetics.** Accept the cognate-key-first lean, or build the IPA channel up front for
  listening exercises?
- **Learner pool.** Restrict candidates to pairs where at least one side's best sense is
  B2 or easier, as measured here, or go wider?

## Out of scope

- Fixing OMW coverage holes (*embarazada*, *parents*). That is new-lemma mapping, in the
  backlog.
- New `lang-tutor` exercise types beyond showing the warning and using a false friend as
  a distractor.
- Shipping any CC-BY-SA pronunciation data.

## Done when (draft)

- The gold-set recall and sampled precision are reported for the chosen generator.
- An approved verifier run has landed in `data/curated/false_friends.jsonl`.
- The rebuilt corpus has a populated `false_friends` table, and the gate passes.
- `/api/v1/lemmas/{id}/false-friends` returns real edges, and `lang-tutor` shows at least
  the warning.
