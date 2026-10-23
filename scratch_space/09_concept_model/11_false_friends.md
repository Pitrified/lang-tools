---
status: planned
---

# Phase 11 - false friends and cognates

> Plan of record (2026-10-22). It runs **before** phase 10 (licensing), so any new source
> it pulls in (a pronunciation tool or lexicon) is license-checked with the rest.

## Goal

Answer one question for every word a learner meets: **does it look like a word I already
know, and if so, does it mean the same thing?**

The learner this is built for knows **en** and **it** fluently and is learning **pt**.
For them a pt word falls into one of three cases:

- **A trap:** a false friend of an en or it word. pt *esquisito* (weird) looks like en
  *exquisite*, and pt *burro* (donkey) looks like it *burro* (butter).
- **Free:** a true cognate of a known word. pt *nação* = it *nazione* = en *nation*. Not
  an interesting new word, but useful to know: it is easier than its band suggests, even
  when both words are rare.
- **Neither:** nothing known looks like it.

So the dataset stores **pairwise look-alike edges** between lemmas of two languages, each
with a `kind`. The per-learner answer is computed at read time, as the union over that
learner's known languages. Adding es or fr later only adds edges, and the same query then
aggregates over them.

What already exists:

- `FalseFriendRelation`, a symmetric lemma-level edge stored once in canonical order,
  with `similarity_score` and per-language `explanation_notes`;
- the store lookup `get_false_friends_for_lemma`;
- `GET /api/v1/lemmas/{id}/false-friends`.

The table has 0 rows. What never existed is a way to **find** the pairs. Phase 7 noted
that "no source supplies them", and phase 8 deferred them because "candidate generation
needs designing first". That design is this phase.

## Kinds of look-alike pair

| Kind | Example | Meaning overlap | Stored |
| --- | --- | --- | --- |
| `full` false friend | en *exit* / es *éxito* (success), pt *esquisito* (weird) / en *exquisite* | none | edge |
| `partial` false friend | en *assist* / pt *assistir* (assist, but mostly watch / attend) | a minor sense only | edge; the note says which sense |
| `cognate` | pt *nação* / it *nazione* / en *nation* | the main sense | edge |
| look-alike noise | en *festival* / pt *feia*, en *cash* / pt *caos* | none, and nobody confuses them | nothing |

Noise is why "similar spelling plus no shared concept" is not a definition. A trap needs
both a strong resemblance (usually a shared root) and a meaning that diverged.

## Measurements (2026-10-22, current corpus)

These were taken before the scope settled, over a narrower pool than the plan now uses:
single lowercase words of at least 4 letters with a best sense of B2 or easier, about
2,500-3,500 lemmas per language. The gold check was 41 classic pairs written from memory
across en-{pt,es,fr,it} and es-pt.

1. **Coverage holes.** 7 of the 41 cannot be found because a lemma is missing from OMW:
   en *parents* (plural only), es *embarazada* (feminine), es *constipado*, pt
   *eventualmente*, es *rato*. New-lemma mapping (backlog) is the fix, not this phase.
2. **Spelling alone is noise.** Jaro-Winkler at least 0.88 with no shared concept gives
   2,300-3,800 candidates per language pair. Most of them are one of three things:
   - inflections: *amigo* / *amiga*, *compra* / *comprar*;
   - OMW gaps: cognates with no shared concept only because the other wordnet lacks the
     sense, such as en *conclusion* / pt *conclusão*;
   - short collisions: *cast* / *casa*.
3. **Spelling plus a main-sense test** catches **26 of the 33** gold pairs present. The
   test asks whether the look-alike is a translation of the word's *best* sense, in either
   direction, and it needs an exact translation match: a fuzzy match filed *soap* /
   *sopa* as a cognate, because *sopa* translates to *soup*. The 7 misses fall in two
   groups:
   - **5 where the spelling diverges** (Jaro-Winkler under 0.85): *push* / *puxar* 0.63,
     *actually* / *atualmente* 0.74, *library* / *livraria* 0.82, *factory* /
     *fattoria* 0.82, *lunch* / *lanche* 0.84;
   - **2 caused by OMW errors**: OMW-fr puts *librairie* (bookshop) in *library*, and
     OMW-pt maps *assistir*'s main sense to *assist*.
4. **Precision is the hard part.** That recall-oriented rule still keeps 5,200-8,700
   candidates per language pair in the narrow pool, and the pool is now wider. So the
   generator supplies recall; ranking plus a verifier supply precision.

## Decisions (settled 2026-10-22)

1. **Language pairs: target x known.** For this learner that is **pt-en** and **pt-it**.
   en-it is left out: both are known, so its traps teach this learner nothing. es and fr
   come later with the same pipeline, and the read-time aggregation needs no change to
   take them.
2. **Wide word range.** There is no CEFR bound. Any single-word lemma qualifies, because
   two hard words that look alike are easier to learn, and that is worth knowing. The
   cost is a larger candidate set, handled by blocking on the cognate key (step 2).
3. **Cognate key first.** Deterministic spelling-correspondence rules generate the
   candidates. The IPA channel (espeak-ng plus PanPhon) is added in step 3 **only if** the
   gold set shows spelling-divergent pairs the key still misses.
4. **One edge table with a `kind`:** `full`, `partial` or `cognate`. This refines the
   earlier "kind = full | partial, cognates stored separately". The per-learner question
   needs all three in one read, so a separate cognates output would mean two queries and
   two gates for one answer. The table is empty, and `lang-tutor` moves in lockstep, so
   the change is cheap now:
   - `FalseFriendRelation` becomes `LookalikeRelation`, and the `false_friends` table
     becomes `lookalikes`, so a cognate is not stored as a "false friend";
   - `get_false_friends_for_lemma` and `/false-friends` stay, filtered to `full` and
     `partial`;
   - a `get_lookalikes_for_lemma` and a `/lookalikes` endpoint return all three kinds.
5. **Gold set: 200 pairs, hand-written and fully reviewed by me** (no paid model). Each
   pair is checked against the corpus (both lemmas exist, their senses) and labelled with
   its kind and a one-line reason. It is about 100 pt-en and 100 pt-it, roughly:
   - 110 false friends, `full` and `partial`;
   - 50 cognates, including rare-but-similar ones (decision 2);
   - 40 look-alike-noise negatives, so precision can be measured as well as recall.

   It is committed as `data/curated/lookalike_gold.jsonl`.

## Brainstorm notes behind the decisions

### Fuzzy distance: a generator, not a classifier

Spelling distance is cheap, deterministic, and already catches 26 of 33. But it cannot
see meaning, and it misses pairs that differ in spelling but not in root (*push* /
*puxar*, *factory* / *fattoria*, *actually* / *atualmente*).

Raw Jaro-Winkler also favours shared prefixes (*festival* / *feia* scores 0.85). Better
metrics are normalized Levenshtein with a length-ratio guard, or the longest common
subsequence ratio used in cognate detection, plus a minimum similarity that rises as
words get shorter.

### The cognate key

The key rewrites each form with cross-language spelling correspondences before comparing:

- suffixes *-tion* / *-ção* / *-zione*, *-ty* / *-dade* / *-tà*;
- *ct* -> *t* (pt) and *ct* -> *tt* (it);
- *ph* -> *f*, *th* -> *t*, *y* -> *i*;
- *x* / *ch* / *sh* / *sc* collapsed;
- doubled consonants collapsed;
- final vowels stripped.

Examples:

- *factory* -> `fatori` and *fattoria* -> `fatori`;
- *actually* -> `atual` and *atualmente* -> `atual`;
- *push* -> `pus` and *puxar* -> `pusar`, which come out close.

The rule table is reviewable and has no dependencies. The key also serves as the
**blocking index** that keeps the wide range tractable: only pairs sharing a key prefix
are compared, not 46k pt x 149k en.

### IPA

**We have none.** OMW 1.4 ships no pronunciations, and Wiktionary's `sounds` left with
kaikki (CC-BY-SA, dropped in 5.5). If step 3 is needed, these are the candidate sources:

| Source | Coverage | Kind | License (verify in phase 10) |
| --- | --- | --- | --- |
| espeak-ng | all five languages | rule-based program with dictionaries; good on pt / it, uneven on en | GPL-3 program; only its output is stored |
| Epitran | pt, it (and es, fr); en needs Flite's `lex_lookup` | rule-based Python library | MIT |
| CMUdict | en, about 134k words (ARPAbet -> IPA) | lexicon | BSD-style |
| WikiPron / Wiktionary IPA | all five, curated by people | scraped lexicon | CC-BY-SA: at most an evaluation reference, never shipped |
| PanPhon | any IPA | articulatory features plus a feature-weighted edit distance | MIT |

pt and it spelling is shallow, so spelling plus correspondences already approximates
sound. English is the deep orthography, and that is where automatic pronunciation is
least reliable. Hence measure first.

### The meaning test

"Meanings differ" has to survive sparse non-English wordnets, where a missing link looks
like a different meaning. The signals, combined:

- **(a) no shared concept**: too weak alone;
- **(b) main-sense test**: as measured above, through English for pt-it. It is also what
  tells `partial` from `full`;
- **(c) concept distance**: Wu-Palmer or path similarity between the two best concepts
  over our hypernym graph (phase 7). It is free and deterministic, and separates
  *soup* / *soap* from *notable* / *notably*;
- **(d) part-of-speech and derivation guard**: *compra* / *comprar* is a relative, not a
  trap. Gloss embeddings were considered and dropped: they cost a paid call and add
  little over (c) plus the verifier.

### The verifier and notes

This step reuses the phase-8 loop:

1. Ranked candidates go to a classifier chain, grounded in both lemmas' senses with
   their glosses and translations.
2. The chain picks the kind and writes `explanation_notes` in **en** (the learner reads
   en). For example: "pt *esquisito* means weird or odd; en *exquisite* is *requintado*."
3. The output goes to a reviewable JSONL and then to `data/curated/lookalikes.jsonl`,
   keyed on lemma ids (stable since phase 8 step 9) and applied at build (the 5.58 rule).
   OMW errors like *librairie* surface as a side effect.

**Sample-measured and approved before any paid run.** The volume is larger than first
estimated because the range is wide. The plan is to rank, cap per pair at a number set
from the gold-set precision curve, and report cost on a sample first.

## Steps

1. **Gold set.** 200 pairs as in decision 5, plus a scorer that reports recall per kind
   and precision on the negatives. This is hand work and costs nothing.
2. **Deterministic candidates.** The cognate key (rules plus blocking index), a better
   spelling metric, the main-sense test, concept distance, and the part-of-speech /
   derivation guard. Each candidate gets a provisional kind and a score. Report gold
   recall and precision, and candidate counts per pair, over the full lemma range.
3. **IPA channel, only if step 2 misses the spelling-divergent gold pairs.** espeak-ng
   plus PanPhon as an extra ranking feature; the license is noted for phase 10.
4. **Model change.** `LookalikeRelation` with `kind`, and the `lookalikes` table: codec,
   SQLite schema, cache version bump, the store helpers (both lookups), the two
   endpoints, and `frozen_api.md`. No data yet.
5. **LLM verifier plus notes** on the ranked candidates. A sample run first, then cost and
   quality reported against the gold set, then approval, then the full run. Accepted
   rows land in `data/curated/lookalikes.jsonl`.
6. **Build input and gate.** The curated file is applied at build. Gate invariants:
   - both endpoints exist, and the pair spans two languages;
   - canonical order, no self-pairs, no duplicates;
   - `kind` is valid;
   - every `full` / `partial` edge has an en note.
7. **Per-learner read (the aggregation).** `CardQuery` and `lemma_card` take
   `known_languages`. The card gains `lookalikes`: language -> the known-language look-alikes
   and their kinds, so the trap / free / neither answer is visible. `CardQuery` gains a
   filter on it (for example only traps, or excluding cognates). Adding a known language
   is just one more list item.
8. **Surface in `lang-tutor`.**
   - Known languages become a setting, defaulting to `["en", "it"]` for now.
   - The lemma page shows traps as warnings and cognates as "looks like it *nazione*".
   - Pair matching may use a false friend as a distractor.
   - Selection gets a mild down-weight for a cognate of a known word.

## Progress (2026-10-22)

**Step 1, gold set: done.** 200 pairs in `data/curated/lookalike_gold.jsonl`, all
hand-written and checked against the corpus. That is 114 pt-en and 86 pt-it: 73 full
and 43 partial false friends, 55 cognates and 29 noise pairs. 14 pairs from the first
draft were dropped because a lemma is missing from OMW (pt *eventualmente*, it
*squisito*, ...).

**Step 2, deterministic candidates: done** (`ingestion.lookalikes`).

- `cognate_key` applies suffix families, sound spellings, the prothetic *e-*,
  infinitives (verbs only) and *-ly* (adverbs only). Suffixes are read before accents
  are folded, so *balcão* is not a *-ção* noun.
- Blocking uses the key prefix or the consonant skeleton.
- `select_candidates` keeps the best 2 per (pt word, known language) at similarity
  0.75 or more, with a known-side Zipf floor of 2.0. The rank prefers the same key,
  then the same part of speech, then similarity, then exact spelling, then frequency.

| Full corpus | Candidates | Gold full | Gold partial | Gold cognate | Noise through |
| --- | ---: | ---: | ---: | ---: | ---: |
| raw (0.65) | 671,596 | 71/73 | 42/43 | 50/55 | 22/29 |
| selected | 65,266 (pt-en 33,586, pt-it 31,680) | 68/73 | 41/43 | 49/55 | 7/29 |

**Step 3, IPA: not added.** The false-friend misses are morphological (*sair* /
*salire*, *mesa* / *mensa*, *ofício* / *ufficio*), and the cognate misses are old sound
changes (*olho* / *occhio*). A pronunciation channel would recover one or two pairs, at
the cost of a dependency and a license question.

**Step 4, model change: done.** `LookalikeRelation` with `kind` in a `lookalikes`
table, `get_lookalikes_for_lemma` and `/lookalikes`.

**Step 5, verifier: chain and loop done; the full run waits for approval.**
`llm.lookalike_verify` takes 20 pairs per request. Measured live on the 200 gold pairs,
with costs at batch prices:

| Model, prompt | Traps found (of 116) | False alarms | Gold sample |
| --- | ---: | ---: | ---: |
| `gpt-6-luna` v1 | 92 | 10 | $0.004 |
| `gpt-5.6-luna` v1 | 93 | 10 | $0.008 |
| `gpt-6-luna` v3 | 93 | 13 | $0.004 |
| `gpt-6.1-sol` v3 (reasoning low) | 106 | 6 | $0.085 |
| `gpt-6.1-sol` v4 | 108 | 7 | $0.088 |
| `gpt-6-luna` v4 | 80 | 7 | $0.004 |
| **`gpt-6.1-sol` v5 + root rule** | **106** | **6** | $0.097 |

How the prompts changed, from what the measurements showed:

- **v2 / v3:** identical forms are never `unrelated` (v1 called *data* / *data*
  unrelated, reasoning from etymology).
- **v4:** same-root relatives in another word form count as cognates. On real
  candidates, sol had called *resiliente* / *resilience* a false friend.
- **v5:** the model also answers `same_root`. A `full` / `partial` verdict then stands
  only when the words share a root or are near-identical (`is_trap`). That removes the
  mid-strength coincidences sol kept flagging (*castigo* / *casting*, *facção* /
  *fiction*) without losing gold traps.

On 200 random selected candidates, v5 gives:

- `gpt-6.1-sol`: 30 traps, 83 cognates, 87 unrelated; full run about **$27** at
  batch prices;
- `gpt-6-luna`: 23 traps, mostly misjudging; full run about **$1.15**.

**Paid run on hold (2026-10-22).** Asked for approval with the numbers above; the user
chose to hold and review the prompt and the numbers first. Acceptance, when it runs,
is a sampled review per language pair (as for the gloss backfill).

**Steps 6-8: built against test data (2026-10-22).** Everything downstream of the
run is ready, so an approved run only needs to land its reviewed file.

- **6, build and gate.** `build_initial` turns the accepted rows of
  `data/curated/lookalikes.jsonl` into `lookalikes` edges once the lemma set is
  final, tagged `manual` / `llm`. Stale rows are counted, never fatal, and the
  counts reach `BuildSummary` and `_build.json`. The gate invariant
  `invalid_lookalike_edge` checks endpoints, the two-language rule, canonical
  order, duplicates, the kind, and the English note on every false friend.
- **7, per-learner cards.** `CardQuery.known_languages` fills
  `LemmaCard.lookalikes` (`LookalikeHint`, false friends first) in one batched read
  per page. `CardQuery.lookalike = trap | cognate | none` filters on them,
  relative to the known languages, and the card endpoints take `known_languages`.
- **8, `lang-tutor`.**
  - `LearnerParams`: target `pt`, known `en,it`, from the environment.
  - Every card read names the known languages.
  - Selection: traps x1.3, cognates x0.7.
  - Pair matching: one false-friend decoy whose wrong tap shows the trap note.
  - The lemma page: a "Looks like" box.

Tests use fixture edges only. The real corpus keeps 0 edges until an approved,
reviewed run lands.

**Gold set expanded to 1000 pairs (2026-10-23).** I hand-labelled 800 more pairs, drawn
from the selected candidates (`GoldPair.origin`):

- 450 drawn at random, which measures precision on the real mix;
- 350 from the near-identical selected candidates, where the hard calls are.

Totals: 169 false friends (105 full, 64 partial), 488 cognates and 343 coincidences. The
real mix is mostly cognates and coincidences: only 52 of the 800 sampled pairs are traps.
Measured on the sampled 800, the generator's provisional kinds give:

- `cognate`: 316 of 324 are true cognates; the other 8 are traps;
- `full`: about 6 in 7 are coincidences.

**Prompt caching (2026-10-23).** It works on the public API, but only above 1024 prompt
tokens, and only explicit breakpoints avoid a 1.25x write on every variable tail. The v5
static part is about 800 tokens, so no call so far was cached. Details, scripts and an
unread batch probe are in [`11_false_friends/prompt_caching.md`](11_false_friends/prompt_caching.md).

### Review through the agent harness (2026-10-23)

The user trusts the hand-labelled pairs more than a cheap model, and the Claude
subscription is a flat rate. So instead of a paid verifier run, the candidates are
reviewed by agents (this harness), in batches spread over weeks within the
subscription's limits. The OpenAI path stays available: the chain, prompts v1-v5, the
cached v6 draft and the 1000-pair experiment harness.

- **Order by usefulness** (`lookalike_review.build_worklist`, committed as
  `data/curated/lookalike_worklist.jsonl`):

  | Tier | Pairs | What |
  | --- | ---: | --- |
  | A | 5,499 | pt word very common (Zipf 4.5 or more) |
  | B | 6,701 | likely traps: near-identical or same-key pairs that the generator calls false friends, pt Zipf 2.5 or more, most common known word first |
  | C | 12,397 | the rest of pt Zipf 3.5 to 4.5 |
  | D | 17,490 | pt Zipf 2.5 to 3.5 |
  | E | 22,214 | the rare tail, last or never |

  Gold pairs stay out of the worklist and are imported directly (`import-gold`, tagged
  `manual`).
- **Batches.**
  - `serve` reserves 100 items under a lock and mixes in 5 hidden gold pairs.
  - The reviewer writes one compact line per item (`N c|p|f|u[!] [note]`).
  - `apply` validates the whole batch (every item, a note on every trap). It then appends
    to `data/curated/lookalikes.jsonl` (`unrelated` as rejected), tagged `agent-review`,
    with the batch id and the guide's hash, and logs the batch's numbers and gold
    agreement to `data/curated/lookalike_review_log.jsonl`.
  - Edges built from these rows carry the source `agent`.
- **Rules and context.**
  - `docs/guides/lookalike_review.md` is the rulebook: the four kinds, the hard cases (my
    calls from labelling the gold set), notes, edge cases and the label format.
  - The `.claude/skills/lookalike-review` skill is one batch's workflow.
  - One subagent per batch, so each starts from a small context. The orchestrating
    session only sees a four-line report per batch.
- **Edge cases.** `!` after the letter marks a judgement call (*fogo* / *fog*). It is
  applied as labelled and counted per batch, for a second look later.
- **Effort.** Labelling the 800 gold pairs inline grew the context by about 89k tokens,
  about 110 per pair. Most of the cost was re-reading a long conversation on every call,
  which subagents with fresh contexts avoid. The 1,000-pair calibration batch (10
  subagents) is the real measurement: the user reads the limit meter before and after.

**Calibration: the first 1,000 tier-A pairs (2026-10-23).** Ten subagents ran in
parallel, one 100-pair batch each (`a0001`-`a0010`):

- **Speed and size:** about one minute each, 4 to 5 tool calls, 70k to 73k tokens per
  subagent (about 720k in all). Most of that is fixed overhead: the system prompt, the
  skill and the guide. Batches of 200 would roughly halve the cost per pair.
- **Agreement:** 49 of 50 hidden gold pairs agreed. The one miss is *bloco* / *bloc*,
  gold cognate, reviewer partial; both are defensible.
- **Results:** 52 full and 27 partial false friends, 248 cognates and 673 unrelated, with
  51 edge cases. The gold set's 1000 pairs were imported as `manual` rows alongside.
- **Good finds:** *legal* (BR cool), *equipe* / *equip*, *empresa* / *empress*,
  *polícia* / *policy*, *maior* / *mayor*, *próprio* / *proper*, *fato* / *fate*,
  *dados* / it *dado*. Inflected forms are a real trap: *precisa* (needs), *era* (was),
  *fez* (did).
- **Rule questions the reviewers raised.** Tier A is full of function words, and the
  near-identical rule turns them into false friends a learner is never fooled by: *com*
  / *come*, *mas* / *mass*, *sem* / it *seme*, *para* / *par*, *tal* / *tall*.
  Reviewers also called pairs like *caso* / it *casa* false friends, although Italian has
  its own *caso*. Both refinements were adopted in the guide on 2026-10-23, from batch `a0011` on; the
  first 1,000 agent rows were not re-labelled:
  1. A grammatical word (preposition, conjunction, article, pronoun) is `u` unless its
     meaning has drifted from a shared root.
  2. When the known language has its own direct cognate of the pt word, a near-identical
     different known word does not mislead: `u`.
- **Corpus sense errors found on the way:** *seja* shows the unit "are", *cada* a
  Laotian coin, *dela* the pig genus. These are homograph senses leaking into function
  words, worth a later data-quality pass.

**Second calibration: two 200-pair batches under the refined rules (2026-10-23).** Two
subagents, `a0011` and `a0012`, 200 tier-A pairs plus 5 hidden gold each:

- **Cost:** 84k and 85k tokens, 6 tool calls, 80 to 100 seconds each. That is about 420
  tokens per pair against about 720 at 100 per batch: the fixed overhead (about 60k) now
  spreads over twice the pairs. The remaining 62.9k worklist items would take about 26M
  tokens at this size, about 315 subagents.
- **Agreement:** 10 of 10 gold pairs agreed (59 of 60 across all 12 batches).
- **Results:** 140 cognate, 245 unrelated, 12 full and 3 partial false friends, 14 edge
  cases. The false-friend rate dropped from 8% to 4% as the two rules turned look-alikes
  such as *ali* / *alike*, *carro* / it *caro* and *visto* / *vista* into `u`, and as the
  tier moves away from the most common words.
- **Worth a second look:** *amo* / it *amo* was labelled `f`, but both languages use *amo*
  for "I love", so it is at least `p`; *copa* / en *cope* is a near-identical `f` nobody
  would confuse.


## Near-identical rule tightened (2026-10-23, from `a0021` on)

Batches `a0013` to `a0020` (1,600 pairs) labelled short near-identical pairs against common known
words as `f!` (pt *dado* / en *dad*, *cabo* / *cab*, *belo* / *bell*), following the guide's old
wording, though nobody would confuse them. Two agents raised it independently. The guide now
asks for `f` only when a learner could plausibly read one word as the other; a short shared stem
nobody maps across is `u`. Earlier rows were not re-labelled; they carry `!` and the older
`prompt_sha`, so they are easy to find for a later pass.

## Three rules settled (2026-10-23, from `a0029` on)

Round 3 (a0021 to a0028) left three open questions, raised by agents or by gold misses. The guide
now answers them:

- **Swapped letters.** Two swapped neighbouring letters count as near-identical (pt *sopa* /
  en *soap*).
- **Own cognate versus a closer look-alike.** The known language's own cognate wins only when it
  is spelled at least as close to the pt word as the look-alike. pt *sopa* / en *soap* (gold
  `f`) and pt *branca* / it *branca* (agent `f!`) are `f`; pt *busto* / it *busta* stays `u`. A
  known word that only shares the spelling is not a cognate, so pt *seta* / it *setta* (gold
  `f`) is not blocked by it *seta* (silk).
- **Partial versus full.** A shared sense in ordinary use, even a secondary one, makes the pair
  `p` (pt *guardar* / it *guardare*, pt *brigar* / it *briga*, both gold `p`). Overlapping main
  meanings are `p`, not `c` (pt *andar* / it *andare*, gold `p`).

Under the new rules the gold row pt *busto* / it *busta* was wrong; it is relabelled from
`full` to `noise` (unrelated). Rows from a0021 to a0028 were not
re-labelled; they carry the old `prompt_sha`.

## Out of scope

- Fixing OMW coverage holes (*embarazada*, *parents*): new-lemma mapping, in the backlog.
- es and fr pairs: the next run of the same pipeline.
- en-it pairs, which are not useful to a learner who knows both.
- Multi-word lemmas.
- Shipping any CC-BY-SA pronunciation data.
- New `lang-tutor` exercise types beyond the warning, the distractor and the weighting.

## Done when

- The gold set (200 pairs) is committed, and the chosen generator's recall and precision
  on it are reported.
- An approved verifier run has landed in `data/curated/lookalikes.jsonl` for pt-en and
  pt-it.
- The rebuilt corpus has a populated `lookalikes` table, and the gate passes.
- A pt card read with `known_languages=["en", "it"]` shows its traps and cognates, and the
  `lang-tutor` lemma page displays them.
