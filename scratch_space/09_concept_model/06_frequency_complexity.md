---
status: done
---

# Phase 6 - frequency & complexity

Populate the two per-sense learner signals that share one home on the `Sense` edge:
**frequency** ("how common") and **CEFR complexity** ("how advanced").
Both are subject to the polysemy trap, so both live on the sense, not the bare `Lemma`.
The fields were defined in phase 2 and left empty; this phase fills them for all five
languages, deterministically, inside the build.

Context: [`00-concepts-brainstorm.md`](00-concepts-brainstorm.md) ("Lemma frequency",
"Lemma complexity"), the 5.54 exploration findings, and the 5.58 durability rule.

## Inherited decisions

These are settled; the plan below builds on them rather than reopening them.

> **Frequency is a priority signal, not a hard cap (2026-06-18).**
> We do not hard-filter by frequency: a low-frequency lemma is kept when it is
> well-connected in the graph or pedagogically important (irregular verbs), which a
> top-N cut would wrongly drop.
> Frequency orders enrichment priority and surfaces a learner-facing core; it deletes no
> rows. Context: [`05.4_data_quality.md`](05.4_data_quality.md), "emerging direction" (2).

> **From 5.5 (2026-06-20).** The kaikki-free rebuild carries the inputs from OMW:
> `sense.counts()` / `tag_count` (SemCor, English) as the weights for splitting token
> frequency across senses, and `synset.lexfile` as a coarse difficulty class.

> **From the 5.54 exploration (2026-06-21).**
> - **Two distinct frequency signals, and the concept one propagates.**
>   Lemma token frequency is language-level.
>   SemCor concept commonness (counts summed to the ILI) is concept-level: it correlates
>   0.47 with the independent en frequency list and predicts the *other* language's lemma
>   frequency (es 0.34, it 0.49).
> - **The English sense split is the prior for languages with no sense-tagged corpus.**
>   SemCor covers 17% of en senses (median 2, max 10,742) and zero non-en senses, but
>   senses share the ILI.
>   Caveat: the exploration validated *aggregate* concept-commonness propagation, not that
>   the within-lemma split transfers. There is no other per-sense signal for those
>   languages, so the English split is an approximate prior, always flagged
>   `frequency_is_estimated`.
> - **Complexity is mostly concept-level.** Against Kelly CEFR (en, 24,595 concepts) lemma
>   frequency is the strongest signal (pearson -0.66); commonness and hypernym depth add
>   weaker, same-direction signal.
>   87% of en-easy concepts are also high-frequency in Italian.
>   Caveat: the -0.66 is partly circular, because Kelly's bands were themselves built from
>   corpus frequency. Read it as a consistency check, not independent validation.

> **From 5.58 (2026-09-01).** A rebuild regenerates every column, so any signal computed
> post hoc into the Parquet is silently reverted by the next `build_initial`.
> Frequency and CEFR are therefore **build stages**, not a maintenance pass.

## Measurements taken while planning (2026-09-02)

Numbers from the current corpus (321,082 lemmas / 117,659 concepts / 490,825 senses), so
the plan is sized against reality rather than intent.

**`wordfreq` covers every built language**, and `zipf_frequency` accepts arbitrary forms
(it is not limited to a staged top-N list), which is what makes a per-lemma join possible
at all:

| lang | lemmas | zipf > 0 | multiword | multiword w/ zipf | median zipf |
| --- | --- | --- | --- | --- | --- |
| en | 147,306 | 115,631 (78.5%) | 64,188 (43.6%) | 53,608 | 2.97 |
| es | 36,254 | 28,558 (78.8%) | 14,000 (38.6%) | 11,319 | 3.07 |
| fr | 50,888 | 41,649 (81.8%) | 15,978 (31.4%) | 13,357 | 2.94 |
| it | 41,692 | 35,057 (84.1%) | 8,520 (20.4%) | 7,460 | 2.94 |
| pt | 44,942 | 38,288 (85.2%) | 12,330 (27.4%) | 11,467 | 3.04 |

Two findings this forces into the design:

- **20-44% of our lemmas are multiword** (`chief executive officer`), and `wordfreq`
  answers those by composing the component frequencies rather than measuring the phrase.
  That is a synthetic number wearing a measured number's clothes, so it must be flagged.
- **~15-21% of lemmas get no frequency at all.** `zipf_frequency` returns `0.0` for a form
  below the corpus floor, which is indistinguishable from "measured as never occurring".
  We store `None`, never `0.0`.

**SemCor counts are readable and English-only**, confirmed against the installed wordnets:
`wn`'s `Sense.counts()` returns plain ints (not objects) on `wn` 0.9.5, `omw-en:1.4`
carries them, and a 5,000-sense sample of `omw-it:1.4` carries none.

**The corpus does not persist the ILI.** `Concept` keeps id / definitions / lexfile /
examples, and the grouping key is consumed inside `group_to_records`.
So SemCor counts cannot be joined to concepts from the Parquet alone; the join has to
happen where the ILI grouping is still in hand, which is another reason the enrichment is
a build stage and not a later pass.

## Shape

Three new pieces, all pure and unit-testable, wired into the existing build:

1. **`ingestion/sources/frequency.py`** - the isolated impure loader (one per dataset, the
   5.5 Step-3 pattern): `lemma_zipf(lemmas)` calls `wordfreq.zipf_frequency` per
   `(text, language)` and returns a plain mapping, mapping `0.0` to `None`.
   It also reports the `wordfreq` version for the manifest.
2. **`ingestion/enrich.py`** - the pure core. Takes `TaggedTables`, the zipf mapping and
   the SemCor counts; writes `Sense.token_frequency` / `sense_frequency` /
   `frequency_is_estimated` / `cefr_level` / `cefr_is_estimated` and `Concept.commonness`.
   No I/O, no optional imports, so it is fully testable from in-memory fixtures.
3. **A stage in `build_initial`**, right after `transform` and the curated gloss overrides,
   before `_write_tables`. The sample carve then inherits the signals for free.

`SynsetEntry` gains `member_counts: tuple[int, ...]`, parallel to `lemmas`, carrying the
per-member SemCor count (zero everywhere but English).
`group_to_records` accumulates them into a `{(lemma_id, concept_id): count}` map and a
per-concept total while it already has the ILI group open.

That function currently returns a 5-tuple; a sixth element is past the point where a tuple
reads. It becomes a small frozen `GroupedRecords` dataclass with named fields.
The alternative (keep growing the tuple) was rejected: three call sites already unpack it
positionally and a mis-ordered unpack would be silent.

## The math

Stated explicitly so the implementation has nothing to invent.

**Token frequency.** `token_frequency = zipf(text, language)`, copied onto every sense of
that lemma (it is a property of the form, shared across its senses - as `Sense`'s docstring
already says). `None` when the form is unknown.

**Sense frequency.** Splitting must happen in linear frequency space, not on the log-scaled
zipf. For lemma `L` in language `X` with senses over concepts `C1..Cn`:

- weight `w_i` = the concept's SemCor total (English counts summed over its English senses);
- smoothed share `p_i = (w_i + 1) / sum_j (w_j + 1)` - Laplace, so a zero-count sense keeps
  a floor rather than being zeroed out;
- `linear = 10 ** (token_frequency - 9)` (zipf is log10 of occurrences per billion);
- `sense_frequency = log10(linear * p_i) + 9`, back on the zipf scale so the two fields are
  directly comparable.

`frequency_is_estimated = True` unless **all** of: the language is English, the concept
carried a real SemCor count, and the form is single-word.
Every non-English sense is estimated (borrowed prior), and every multiword sense is
estimated (composed zipf).

**Concept commonness.** `Concept.commonness = log10(1 + semcor_total)`, a new persisted
concept-level field. `None` means the concept has no English member at all; `0.0` means it
has one that SemCor never tagged. Those are different facts and the field keeps them apart.

**CEFR.** A concept-level score plus a thin per-language overlay, per 5.54 Topic 5:

- concept part: normalized commonness (higher = easier) and hypernym min-depth (deeper =
  harder), depth computed in-build by BFS over the hypernym edges the corpus already has
  (117,659 concepts / 97,666 edges, trivially cheap);
- language overlay: token frequency (dominant) and a small form-length term;
- the blend weights and the five score cutoffs are **fit on English against Kelly**, then
  applied unchanged to all five languages. The score inputs are corpus-normalized, so
  re-quantiling per language would only force an identical band histogram everywhere and
  destroy the cross-language comparison we are trying to keep.

Kelly is CC-BY-NC-SA and stays **validation-only, never merged**. The consequence is worth
stating plainly: since no graded list is ever shipped, **`cefr_is_estimated` is `True` for
every sense in every language**, English included. The flag is honest, not decorative.

## Steps

1. **Re-stage the inputs.** `data/_raw/lexicon/staging/` currently holds only the
   gloss-repair files; the 5.54 staged datasets are gone (regenerable by design, 5.5 Q1).
   Re-run `00_stage.ipynb` for the frequency lists and the Kelly en/it lists.
2. **Carry the counts.** `SynsetEntry.member_counts`, read via `sense.counts()` in
   `wn_synset_entries`; `group_to_records` returns `GroupedRecords` with the sense-count map
   and the per-concept totals. Unit tests over fakes, including the English-only asymmetry.
3. **`Concept.commonness`** field + codec schema + a round-trip test.
4. **`ingestion/sources/frequency.py`** and **`ingestion/enrich.py`** per the math above,
   with the depth BFS. Same step: move `wordfreq` to the `ingest` extra, consolidate the
   optional-dependency errors into `ingestion/deps.py`, and fix `_wordfreq_version` to read
   `importlib.metadata` (Decision 3).
5. **Wire the build stage**; record `wordfreq` version and coverage counts in `_build.json`.
6. **Extend the gate** (`lexicon/quality.py`): coverage and estimated-share checks plus new
   invariants (see below), report sections per language.
7. **Rebuild all five languages, re-gate, regenerate the sample seed** (the carve is
   `sample_data_fol`-driven since 5.59, so this is one build).
8. **Validate on en/it** in a new `notebooks/lexicon_enrich/06_validation.ipynb`: band-exact
   and within-one-band agreement against Kelly, plus the fitted weights and cutoffs.
   Recorded, **not gated** - the circularity caveat above is why.
9. `uv run pytest && uv run ruff check . && uv run pyright`; docs + tracking updated.

## Gate additions

The existing four invariants stay. New ones, baselines recorded from the first green build
the same way `DEFINITION_EQUALS_LEMMA_BASELINE` was:

- token-frequency coverage per language does not fall below its recorded floor (~78-85%);
- no sense carries a `sense_frequency` without a `token_frequency`;
- every non-English sense, and every multiword sense, has `frequency_is_estimated` set;
- `cefr_level` is always in `{A1, A2, B1, B2, C1, C2}` or null, and `cefr_is_estimated` is
  true wherever `cefr_level` is set.

## Decisions (settled 2026-09-02)

All four were put to the user as recommendations and answered one at a time; each changed
what gets built, and the reasoning is kept because in three of the four the losing option
had a real argument behind it.

1. **No lemma-level convenience cache** - confirmed, do not cache.
   The draft proposed caching a coarse frequency and CEFR on `Lemma`.
   Phase 2 deliberately removed `Lemma.frequency`, and a cached aggregate is exactly the
   drift-prone denormalization the persisted models were shaped to avoid: every aggregation
   choice is a claim, and `max` says "how common is this word at its most common sense",
   which for `bank` reports the money sense to a learner who just met the river one.
   Consumers reach the signals through the sense edge.

   The ergonomic need behind the draft's proposal is real, though: `lang-tutor` selects
   *lemmas* ("common words at this level"), so answering that through senses is a join plus
   an aggregation at every query.
   **Recorded as one possible solution, not yet a decision:** a `LexiconStore` query method
   that ranks lemmas by their best sense - the same convenience without a persisted column
   that can go stale, and with the aggregation rule visible at the call site where it can be
   changed. If it ever measures too slow, the fix is an index or a load-time derived view,
   never a written field. Should it be built, frequency must aggregate to the *most frequent*
   sense and CEFR to the *easiest*: opposite ends of the sense list, and mixing them silently
   would be a bug.

   `lang-tutor` reads the removed field today (`selection.py:128`) and stays broken until
   phase 9 fixes it against whatever query surface exists then. That is deliberate: patching
   the consumer by reverting a model decision would be the wrong fix, and there is no rush.
2. **Deterministic only; no LLM CEFR judgment in this phase** - deferred to phase 8.
   The draft floated an LLM estimate for pt/es/fr, the three languages with no graded list.
   Two reasons it does not belong here.

   Practical: `build_initial` is reproducible from pinned inputs, and 5.58 already settled
   what to do with LLM output that must survive a rebuild - it becomes a committed file the
   build applies, not a call inside the build. An LLM leg here would either break that
   reproducibility or reinvent `gloss_overrides.jsonl` under a new name. The seam therefore
   already exists in the right place: a `cefr_overrides.jsonl` applied by the build, which
   is phase 8's machinery.

   Decisive: with no graded list in pt/es/fr, **no measurement distinguishes a better
   estimate from a merely different one**. Shipping an unvalidatable refinement on top of a
   validatable baseline costs the ability to say where the numbers came from. Phase 8 can
   run it as a reviewed pass, which is the only quality signal those languages have.

   Phase 6 therefore ships all five languages from the same deterministic score. Nothing is
   missing for pt/es/fr; their estimate is uniform with the rest rather than LLM-adjusted.
   Whether it *needs* LLM help is a judgement to make once the fitted band distributions
   exist, not now - that check belongs in step 8's validation notebook.
3. **`wordfreq` moves from the `enrich` extra to `ingest`** - approved, with the two
   consequences below handled properly rather than papered over.
   Extras group by which code path needs them, not by which phase introduced them. Once
   frequency is a build input, `wordfreq` belongs with `wn` on the build path;
   `xlrd` / `pandas` / `matplotlib` stay in `enrich`, which then matches its own docstring
   (Kelly's `.xls` plus the notebooks). The alternative - requiring
   `--extra ingest --extra enrich` for a build - drags pandas and matplotlib into a build
   environment with no use for them.

   **Consolidate the optional-dependency errors.** Three ad-hoc classes exist
   (`IngestDependencyMissingError` takes no arguments and hardcodes "the 'ingest' extra
   (wn)"; `EnrichDependencyMissingError` takes a package; `StoreDependencyMissingError` is a
   different layer). After the move, the enrich-flavoured error would be telling people to
   install the wrong extra for `wordfreq`.
   Replace the first two with a single `OptionalDependencyMissingError(package, extra)` plus
   a `require_module(package, extra)` shim in a new `ingestion/deps.py`, and route every
   lazy import through it. None of these are exported from any `__init__`, so this is an
   internal consolidation, not an API break; it touches ~8 call sites, their `Raises:`
   docstrings, one test, and one line of `docs/library/lexicon.md`.
   `StoreDependencyMissingError` (pyarrow/duckdb, runtime layer) stays where it is - it is
   not on this path.
   Deliberate behaviour change: `staging.frequency` now reports the **ingest** extra,
   because that is where `wordfreq` lives; its test updates to match.

   **Fix the version pin, which is currently broken.** `_wordfreq_version()` does
   `getattr(wordfreq, "__version__", "unknown")`, and `wordfreq` exposes no `__version__`
   (verified 2026-09-02), so it has silently returned `"unknown"` since 5.54 and every
   staging manifest entry it wrote records that. Use
   `importlib.metadata.version("wordfreq")`. This is load-bearing for the phase: "the build
   is reproducible from pinned inputs" is false while the frequency source's pin is the
   literal string `unknown`.

   Two `wordfreq` call sites remain and that is correct, not duplication: `staging.frequency`
   writes a top-N `(word, rank, zipf)` list for exploration, while `sources.frequency`
   answers per-lemma zipf for arbitrary forms including multiword. Different questions, same
   library; only the lazy-import shim is shared.
4. **Depth is computed, not persisted** - confirmed, with the ceiling named below.
   Hypernym `min_depth` feeds the CEFR score and is recomputed by BFS on every build (97,666
   edges over 117,659 concepts, well under a second). No column.

   The reason it is *not* obvious, recorded for whoever wonders later: "derivable from the
   shipped edges" is true on paper and misleading in practice. Phases 3 and 4 shaped the
   store around **point lookups and bounded adjacency joins, not aggregations**, and
   depth-to-root is an unbounded traversal. So a consumer cannot cheaply derive it through
   the query surface that actually exists - the same argument that justifies persisting
   `commonness`, arriving one step later.

   What breaks the tie is that no consumer needs depth today: what ships to a learner is the
   CEFR band, and depth is already folded into it. A column on the chance someone later
   wants the raw specificity signal is speculative generality. (5.54 Topic 4 asked phase 6
   to expose a *connectivity* metric - that is degree, a bounded neighbour count the store
   answers fine, not depth.)

   **The ceiling, stated so the next person does not walk into it:** if a consumer ever does
   need depth, or any other whole-graph derived quantity, the fix is to **persist it from the
   build**, never to traverse at query time. A runtime BFS over 117k concepts through the
   SQLite surface is a performance bug of precisely the kind phase 5.3 spent a phase
   removing (the >5 min load). Adding the column later is cheap; discovering the traversal in
   production is not.

## Out of scope

- Semantic relations beyond the hypernym edges already built (phase 7).
- Tatoeba examples (5.54 Topic 1 deferred them: sense-blind join, CC-BY).
- Exposing these signals in exercises - that lives in `lang-tutor` (phase 9).
- Any pruning of the long tail. Frequency ranks, it does not delete.

## Result (2026-09-02)

Built and gated on the five-language corpus. Row counts are **unchanged**
(321,082 lemmas / 117,659 concepts / 490,825 senses / 97,666 hypernym edges) -
this phase adds columns, not rows - and all **eight** invariants pass, the four
from 05.56 plus the four added here.

| measure | value |
| --- | --- |
| senses with a token frequency | 425,077 of 490,825 (86.6%) |
| per-language coverage | en 83.7%, es 86.2%, it 88.3%, pt 89.4%, fr 89.9% |
| senses flagged `frequency_is_estimated` | 460,587 (93.8%) |
| senses with a CEFR band | 490,825 (100%), all estimated |
| concepts with `commonness` | 117,659 (90,404 counted zero, 27,255 positive) |
| `wordfreq` pin in the manifest | 3.1.1 (was the literal string `unknown`) |

### The cutoffs were guesses, and the data said so

The first build used hand-picked cutoffs and the docstring claimed they were
"calibrated on English against Kelly". They were not, and validating them showed
it: 20.8% exact agreement, 49.4% within one band, systematically **easier** than
Kelly on the words Kelly covers. Fitting them properly - matching Kelly's own band
proportions on the English subset - roughly doubled both figures.

Final measurement against Kelly, on the shipped corpus:

| | en | it |
| --- | --- | --- |
| forms matched | 6,561 | 4,534 |
| exact band agreement | 41.2% | 19.5% |
| within one band | 74.4% | 59.4% |
| mean offset (bands) | +0.17 | +1.23 |
| rank correlation (Spearman) | 0.632 | 0.661 |

**82% of the corpus lands in C2, and that is not a miscalibration.** Kelly grades
the 7,549 most frequent English words, so its own "C2" means "least frequent of
the common head", not "hardest word in the language", while WordNet is
overwhelmingly specialist vocabulary sitting past the end of any graded list. Our
C2 is therefore a catch-all "past the syllabus" bucket, and the bands that matter
to a learner (A1-B1, ~7.7% of senses, ~38k) are the ones Kelly can speak to. The
alternative - keeping a pretty histogram with bands that do not correspond to
CEFR - is worse for the one query the tutor actually makes.

**What Kelly can and cannot settle.** It validates the *ordering*: rank
correlation 0.632 (en) and 0.661 (it), and the Italian figure is the meaningful
one, because the cutoffs were fitted on English alone and Italian still orders
correctly. It cannot fix the absolute scale per language: Italian sits +1.23 bands
harder than Kelly-it. That is recorded as a measured limitation rather than
corrected, because a per-language offset needs a graded list per language and
three of the five have none. Both figures carry 5.54's circularity caveat - Kelly
was itself built largely from corpus frequency, the heaviest term in our score.

### Findings worth keeping

- **Kelly lists a word once per part of speech** (7,549 rows, 6,756 forms;
  `round` appears at three levels). The first join double-counted duplicates. A
  repeated form now keeps its **easiest** band, mirroring the easiest-sense rule
  on our side; this alone moved English agreement 38.3% -> 41.2% and the rank
  correlation 0.555 -> 0.632.
- **`_wordfreq_version` was silently broken**, as predicted while planning: it
  read a `__version__` attribute `wordfreq` does not define, so every staging
  manifest entry since 5.54 recorded `"unknown"`. Now read from
  `importlib.metadata`, and the build manifest pins 3.1.1.
- **`Concept.commonness` is never `None` in this build.** Every concept has an
  English member (the build includes `en`, and every synset is ILI-linked), so the
  "no English member" case the field distinguishes does not arise here. The
  distinction is kept anyway, on the same reasoning as the CILI gloss fallback:
  dormant for English-inclusive builds, correct for English-excluded ones.
- **A misaligned `member_counts` raises** rather than zip-truncating. Truncation
  would silently attribute one word's SemCor count to another.
- **Spot-check on `bank`**: all senses share the token frequency 5.16, and the
  split orders them river-bank 4.74 > financial 4.64 > the rare verb senses 3.80,
  all flagged measured. SemCor really does rank the river sense first, so the
  weights are doing visible work rather than smoothing everything flat.
- **The A1 band reads like learner vocabulary** (`soon`, `hand`, `enter`,
  `receive`, `eat`, `ask`), but 7.8% of its English senses are forms of two
  characters or fewer, including roman numerals like `II`. Not a phase-6 defect -
  they are legitimate high-frequency OMW member forms - but the same member-form
  quality question 5.57 opened. **Routed to phase 8**, not fixed here.

### Deviations from the plan

- **No `require_module` shim.** The plan called for one alongside
  `OptionalDependencyMissingError`; building it would have erased the type
  checker's view of `wn` (an `importlib` shim returns a bare `ModuleType`). Each
  site keeps its literal `import` and the consolidated error, which was the part
  that actually mattered.
- **`RELATION_HYPERNYM` added** to `relations.py`. The hypernym edge type was a
  string literal in `sources.omw`; the depth BFS needed to filter on it, and two
  call sites for one literal is where a constant earns itself.
- **Kelly validation lives in a package module**, `ingestion.cefr_validation`, not
  in notebook cells - the repo rule is thin notebooks, and the re-fit has to be
  re-runnable when the score changes.

## Done when

- [x] Senses carry token frequency, sense frequency and a CEFR band for all five languages,
      each with its `*_is_estimated` flag set truthfully.
- [x] `Concept.commonness` is populated and round-trips through the codec.
- [x] A full rebuild reproduces every signal from pinned inputs, with no post-hoc step.
- [x] The gate carries the new invariants and the report shows per-language coverage,
      estimated share and band distribution.
- [x] en/it validation against Kelly is recorded with its agreement numbers.
- [x] `uv run pytest && uv run ruff check . && uv run pyright` green (258 passed); docs + tracking updated.
