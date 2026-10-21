---
status: planned
---

# Phase 8 - maintenance (LLM-based)

The dataset is not build-once: new lemmas arrive, glosses need filling, and member-form and
slug quality drift. This phase turns the one loop phase 5.55 built (thin-gloss repair) into
the general upkeep machinery, and runs it on the worklists earlier phases routed here.

Context: [`00-concepts-brainstorm.md`](00-concepts-brainstorm.md), "Bootstrap source" (LLM
mapping) and "Uplift plan". The machinery already exists in one instance:
`lexicon/maintenance.py` (worklist -> chain -> reviewable JSONL -> apply) and the 05.58
durability rule (accepted output becomes a committed `data/curated/*.jsonl` the build
applies; a post-hoc Parquet edit is reverted by the next rebuild).

## Inherited hand-offs

> **From 5.55 (2026-07-11).** Slug **tier 2**: an LLM picks a 1-3 word qualifier taken from
> the English gloss for each same-lexfile collision group. Already decided: the reviewed
> qualifier table is a **committed build input** keyed by ILI grouping key, run through a
> **Batch API**. Sized then at ~1.5M in / ~0.3M out tokens.

> **From 5.55 (2026-07-11).** Non-English gloss backfill: deferred, "trigger = a consumer
> needing non-en glosses". The `gloss_repair` chain has never run against a live model.

> **From phase 6 (2026-09-02).** LLM CEFR judgment for pt/es/fr, applied as a committed
> `cefr_overrides.jsonl`. "Read phase 6's fitted band distributions first; they say whether
> the deterministic estimate needs help at all."

> **From phase 6 / 5.57.** Member-form review: short A1 English forms (roman numerals),
> French sense spread, ~150 sentence-like non-English forms.

> **From phase 7 (2026-10-21).** `domain_*` / `exemplifies` deferred as "topic metadata,
> better served by phase 8's topics"; false friends "stay an LLM/curation job for phase 8".

> **From phase 7 (2026-10-21).** Open, phase-6 scoped: the shipped `CEFR_CUTOFFS` are not
> what `fit_cutoffs` returns on today's corpus. Not this phase's to decide, listed so it is
> not lost.

## Measurements taken while planning (2026-10-21)

Against the phase-7 corpus (117,659 concepts / 321,082 lemmas / 490,825 senses).

| worklist | size | kind | who consumes it today |
| --- | --- | --- | --- |
| **Lemma topics** | **0 of 321,082 lemmas** carry a topic | deterministic first | `lang-tutor` selection filters on `topics`; the webapp's `?topic=` filter; both return nothing on the real corpus |
| Non-en glosses | **174,319** missing (fr / pt / es 0%, it 5.5%) | LLM | nothing yet |
| Slug tier 2 | **9,782** groups, **23,476** concepts | LLM | legibility only (ids unique via hash) |
| A1 short en forms | 144 of 1,851 A1 senses (digits `1`-`25`, letters, `II`, `US`, `OK`, `at`, `by`, `go`) | review | a learner's A1 pool |
| Sentence-like non-en forms | 931 (fr 393, pt 311, it 160, es 67) | review | exercises built on lemmas |
| False friends | 0 | LLM / curation | `get_false_friends_for_lemma` |
| LLM CEFR pt/es/fr | 117,659 concepts | LLM, unvalidatable | the bands |

Four findings change the hand-offs:

1. **Topics are the real consumer gap.** The previous plans framed phase 8 around glosses
   and slugs, but the one thing a consumer filters on is empty: no lemma in the full corpus
   has a topic (the old hand-written seed had them; the 05.59 build-carved seed does not).
   Deterministic sources exist: every concept carries one of **45** WordNet lexfile classes
   (`noun.food` 2,573, `noun.animal` 7,509, `noun.body` 2,016, ...), and OMW English has
   6,643 `domain_topic` links (phase 7 deferred them here). Also noted:
   `get_lemmas_by_topic` scans every lemma in Python - fine for the seed, the 5.3-class
   performance bug on the full corpus once topics exist.
2. **Non-en glosses are absent, not sparse.** The old "pt 71.5% / es 70.1%" coverage was
   kaikki-inflated; real OMW coverage is 0% outside en and it. Backfill is a translation
   job grounded in the English gloss and the concept's member forms, ~174k items - too many
   for line-by-line human review, so it needs a different acceptance rule than gloss repair.
3. **The LLM provider assumption is stale.** 5.55 sized tier 2 against Anthropic's Batch
   API (Haiku to Opus). `llm-core` exposes OpenAI / Azure / Ollama / HuggingFace chat
   configs and no batch path, and this environment reaches OpenAI (chat and `/v1/batches`
   both answer through the proxy). Cost does not constrain any worklist here: tier 2 and
   the gloss backfill are each order-of-dollars on a small current model, halved by the
   Batch API. Prices to be checked at run time, not trusted from this note.
4. **The CEFR distributions do not argue for an LLM pass.** pt / es / fr show the same band
   shape as en and it (C2-heavy, the expected consequence of Kelly-fitted cutoffs, see phase
   6), and with no graded list in those languages no measurement can tell an LLM band from a
   different one. The hand-off said to read the distributions first; they say "no help
   needed that we could verify".

## Shape

One generalization and a set of worklists that run through it.

**The loop, generalized.** `maintenance.py` today hard-codes one worklist and one override
file. It becomes a small framework: a *worklist* (deterministic query -> typed items with
their grounding context), a *proposer* (an LLM chain or a deterministic rule), a reviewable
JSONL of proposals, and a *curated override file* under `data/curated/` that
`build_initial` applies after `transform`. Gloss overrides keep their file and format; each
new worklist adds one curated file of the same shape (`topic`, `slug_qualifiers`, ...). The
build stays reproducible from pinned sources plus committed curated files, and nothing is
ever edited into the Parquet that a rebuild would revert.

**An LLM runner.** One place that runs a chain over a worklist: OpenAI through `llm-core`,
a resumable JSONL checkpoint (a killed run continues, a finished item is never re-billed),
bounded concurrency for small worklists, and the OpenAI Batch API for large ones. Every
proposal records model, prompt version and timestamp, so an accepted row is auditable for
the phase-10 dataset card.

**Acceptance rules by risk**, rather than one rule for everything:

- *Meaning-changing, small* (gloss repair, new-lemma mapping, false friends): proposal ->
  human `accepted` -> curated file. As today.
- *Mechanical* (slug qualifiers, constrained to words of the English gloss so they cannot
  invent meaning): auto-accepted after the constraint check, sampled for review.
- *Bulk generated content* (non-en glosses): cannot be read line by line. Accepted by
  sampled review plus a provenance tag (`llm`) and the gate, and kept out of anything
  labelled measured.

## Decisions to confirm

Recommendations given; each changes what gets built.

1. **Scope of this phase.** Recommend: the loop generalization + runner, **topics**, slug
   tier 2, the member-form review, and the gloss backfill. Defer new-lemma mapping and false
   friends to a follow-up (no source feeds new lemmas yet; false friends need candidate
   generation designed first). Drop the LLM CEFR pass (finding 4).
2. **Topics: where they live and where they come from.** Recommend a **concept-level**
   `Concept.topics` filled deterministically from a reviewed `lexfile -> topic` table (45
   rows, committed) plus OMW `domain_topic` where present, with `Lemma.topics` derived from
   its senses' concepts at store-build time rather than persisted twice. A topic is a
   property of a meaning ("bank" is `money` in one sense and `nature` in another), the
   same argument that put frequency on the sense. The vocabulary is the tutor's, not
   WordNet's: ~15-25 learner topics (`food`, `animals`, `body`, `travel`, ...), with the
   lexfile mapping reviewed once.
3. **LLM provider and model.** Recommend OpenAI via `llm-core`, a small current model for
   the bulk jobs and a larger one only where a sample review shows the small one failing;
   Batch API for anything over a few thousand items. Supersedes 5.55's Anthropic sizing.
4. **Acceptance for bulk glosses.** Recommend sampled review (e.g. 50 per language) as the
   gate for accepting a backfill run, the `llm` provenance tag on every generated gloss, and
   a quality-report section counting generated vs source glosses. The alternative - no
   backfill until a consumer asks - is defensible (it is what 5.55 decided); the case for
   doing it now is that phase 9 (consumer uplift) will want definitions in the learner's
   language, and the run is cheap.
5. **Where maintenance runs.** Recommend thin notebooks under `notebooks/lexicon_maintain/`
   (the existing pattern) over a CLI or scheduled job; a cadence only makes sense once
   something feeds new lemmas in.

## Steps (assuming the recommendations)

1. Generalize `maintenance.py` into worklist / proposal / curated-override pieces; port the
   gloss loop onto it with no behaviour change (same file, same tests passing).
2. The LLM runner: checkpointed, concurrency-bounded, Batch-API path; exercise the
   existing `gloss_repair` chain against a live model for the first time.
3. Topics: the reviewed `lexfile -> topic` table, `Concept.topics` (codec + store +
   `CACHE_VERSION` bump), lemma topics derived in the store, an indexed topic query; gate
   coverage section. Seed regains topics.
4. Slug tier 2: qualifier chain constrained to gloss words, curated `slug_qualifiers.jsonl`
   keyed by grouping key, applied in `_tiered_slugs`; rebuild re-keys every id and the gate
   checks referential integrity across the churn.
5. Member-form review worklists (A1 short forms, sentence-like forms): deterministic
   candidates, human decisions into a curated drop/keep file the build applies.
6. Non-en gloss backfill: translation chain grounded in the English gloss and members,
   Batch run, sampled review, curated file, gate section.
7. Rebuild + re-gate after each worklist lands; docs, tracking; `uv run pytest && uv run
   ruff check . && uv run pyright` green.

## Gate additions

- Topic coverage per language (concepts and lemmas with at least one topic), and every
  topic in the reviewed vocabulary.
- Curated files: stale entries (keyed on an id or grouping key the build no longer has)
  counted and reported, never fatal - the 05.58 rule, extended to each new file.
- Generated content counted by provenance (`llm` glosses per language), so a backfill run
  is visible in the report diff.

## Out of scope

- The initial bulk ingestion (phase 5); shipping/licensing mechanics (phase 10); exposing
  topics or glosses in `lang-tutor` (phase 9).
- Re-fitting `CEFR_CUTOFFS` (phase 6's decision, listed above).
- Wikidata / kaikki as gloss sources (license and sense-blind-join reasons recorded in 5.5).

## Done when

- [ ] One documented maintenance framework runs every worklist, with resumable LLM runs and
      reviewable, auditable output; the gloss loop runs on it unchanged.
- [ ] Every concept the lexfile table covers carries a topic, and a lemma's topics come from
      its senses; the webapp and `lang-tutor` topic filters return lemmas on the real corpus.
- [ ] The chosen LLM worklists have run, been accepted under their rule, and landed as
      curated build inputs that survive a rebuild.
- [ ] The gate carries the new sections; `uv run pytest && uv run ruff check . && uv run
      pyright` green; docs + tracking updated.
