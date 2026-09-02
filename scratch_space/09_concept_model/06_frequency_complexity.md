---
status: planned
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
   with the depth BFS.
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

## Decisions to confirm

Recommendations given; each changes what gets built.

1. **No lemma-level convenience cache.** The draft proposed caching a coarse frequency and
   CEFR on `Lemma`. Recommend **not** doing it: phase 2 deliberately removed
   `Lemma.frequency`, and a cached aggregate is exactly the drift-prone denormalization the
   persisted models were shaped to avoid. Consumers get it from the store.
   This is also the field `lang-tutor` still reads (`selection.py:128`), which is phase 9's
   break to fix properly, not a reason to resurrect the column.
2. **Deterministic only; no LLM CEFR judgment in this phase.** The draft floated an LLM
   estimate for pt/es/fr. Recommend routing it to phase 8, where the maintenance loop and
   its review step live, and where the LLM chain still needs its first live exercise (5.55
   closed with that chain unrun). Phase 6 stays reproducible from pinned inputs.
3. **`wordfreq` moves from the `enrich` extra to `ingest`.** It stops being an exploration
   dependency and becomes a build input; `xlrd` / `pandas` / `matplotlib` stay in `enrich`.
4. **Depth is computed, not persisted.** It is derivable from the shipped
   `concept_relations` table, so storing it would duplicate the edges. Commonness is
   persisted because it is *not* derivable without re-reading OMW.

## Out of scope

- Semantic relations beyond the hypernym edges already built (phase 7).
- Tatoeba examples (5.54 Topic 1 deferred them: sense-blind join, CC-BY).
- Exposing these signals in exercises - that lives in `lang-tutor` (phase 9).
- Any pruning of the long tail. Frequency ranks, it does not delete.

## Done when

- [ ] Senses carry token frequency, sense frequency and a CEFR band for all five languages,
      each with its `*_is_estimated` flag set truthfully.
- [ ] `Concept.commonness` is populated and round-trips through the codec.
- [ ] A full rebuild reproduces every signal from pinned inputs, with no post-hoc step.
- [ ] The gate carries the new invariants and the report shows per-language coverage,
      estimated share and band distribution.
- [ ] en/it validation against Kelly is recorded with its agreement numbers.
- [ ] `uv run pytest && uv run ruff check . && uv run pyright` green; docs + tracking updated.
