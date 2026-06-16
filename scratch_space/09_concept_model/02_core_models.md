---
status: planned
---

# Phase 2 - core data models

## Overview

Introduce the concept-centric model on top of the thin `Lemma` left by phase 1.
This is the structural heart of the effort: it defines the Pydantic models every
later phase reads and writes. Context:
[`00-concepts-brainstorm.md`](00-concepts-brainstorm.md), "Proposed models",
"Lemma frequency", "Lemma complexity (CEFR level)", and "Semantic relations
beyond false friends". Depends on phase 1 (rename, done) and informs phases 3-7
(storage, store layer, ingestion, frequency, relations).

This phase is **models + id helpers + unit tests only**. It reshapes `Lemma` and
adds `Concept`, `Sense`, `FalseFriendRelation`, and a generic `ConceptRelation`,
all in `src/lang_tools/lexicon/`, plus the deterministic id constructors. It makes
the **minimal mechanical updates** to the existing call sites (`ingestion/`,
`lemma_store.py`, the webapp router, existing tests) needed to keep the
verification suite green - but it does **not** build the concept/sense/edge
registries and indexes (phase 4), the ingestion that fills them (phase 5), or any
frequency/CEFR/relation population (phases 6-7). The new edge/sense fields are
defined now and left empty until those phases.

Note on the brainstorm's illustrative ids: code samples there use readable ids
like `l_banco_pt` / `c_library_place`. The real `lemma_id` produces bare 16-char
hex (phase 1 kept it prefix-free), and the resolved concept scheme is
`c__{slug}__{hash[:12]}`. The readable forms are illustrative only; the models use
the deterministic hashed ids below.

Two layers are kept distinct throughout (confirmed direction, see "Persistence vs
representation"): the **persisted shape** (the thin, id-only records written to
disk - the source of truth) and the **in-memory representation** (the same records
hydrated by the store with convenience back-references so callers can write
`sense.lemma` instead of `get_lemma_by_id(sense.lemma_id)`). Phase 2 defines the
persisted models and the representation *pattern*; the hydration itself needs the
registries and is built in phase 4.

## Goals

1. Reshape `Lemma` to the thin token: keep `text`, `language`, `normalized`,
   `part_of_speech`, `topics`, `examples`, `sources`, and the computed
   convenience fields; drop the heavy fields now owned elsewhere
   (`translations`, embedded `false_friends`, canonical `glosses`, coarse
   `frequency`). No migration - sample data is regenerated in phase 9.
2. Add `Concept` (the language-independent synset; persisted as `id` +
   `definitions` only - `lemmas` is dropped, see goal 3), `Sense` (the explicit
   `lemma_id <-> concept_id` edge and the canonical membership record, hosting
   per-sense frequency and CEFR), `FalseFriendRelation` (decoupled,
   canonically-ordered lemma-to-lemma edge), and a generic `ConceptRelation` stub
   (typed concept-to-concept edge, populated in phase 7).
3. Keep the persisted models thin and free of redundant membership: `Sense` is the
   single source of truth for lemma <-> concept membership, so `Lemma.concept_ids`
   is **not** added and `Concept.lemmas` is **dropped** (both are rebuildable from
   the `Sense` set; persisting them would duplicate the edge and risk drift). The
   convenient navigation views (`sense.lemma`, `concept.lemmas`, ...) are a
   representation-layer concern built in phase 4.
4. Add deterministic id constructors `concept_id` and `sense_id` alongside the
   existing `lemma_id`, with the slug-dedup discipline for colliding concept
   slugs documented.
5. Keep the suite green: update `ingestion/`, `lemma_store.py`, the webapp router,
   and existing tests just enough that the thin `Lemma` constructs and serves as
   before. New unit tests cover id determinism, canonical edge ordering, and
   round-trip serialization.

## Plan

All paths under `src/lang_tools/lexicon/` unless noted.

### `lemma.py` - reshape to the thin `Lemma`

- **Keep**: `text`, `language`, `normalized` (auto-filled validator),
  `part_of_speech`, `topics`, `examples` (`LemmaExample`), `sources`, and the
  computed properties `id`, `has_accent`, `accented_chars`, `length`
  (lang-tutor's Wordle exercise uses `length`/`has_accent`).
- **Drop from the model**: `translations` (cross-lingual links now live implicitly
  via shared `Concept`s), `false_friends` + the `FalseFriend` class (moves to
  `FalseFriendRelation`), `glosses` + `Gloss`/`GlossExample` (canonical glosses
  move to `Concept.definitions`), and `frequency` + the `FrequencyLevel` literal
  (superseded by per-sense `Sense.token_frequency` / `sense_frequency`).
- **Do not add `concept_ids`** (confirmed - the `Sense` edge is the single source
  of truth; lemma <-> concept navigation is the hydrated `lemma.senses` /
  `lemma.concepts` view built in phase 4). This supersedes the scope sketch's
  "add `concept_ids`". See "Persistence vs representation".
- Update the module docstring to describe the thin token and point at `Concept` /
  `Sense` for meaning.

### `concept.py` (new) - `Concept`

- Persisted shape: `id: str` and `definitions: dict[str, str]` (per-language gloss,
  e.g. `{"en": ..., "pt": ...}`). **That is all that is stored.**
- **`lemmas: dict[str, list[str]]` is dropped** (it was the brainstorm's
  membership field). Analysis: with `Sense` as the explicit edge, the per-language
  lemma membership is fully derivable - group the concept's senses, then bucket
  each by its lemma's `language`. Keeping it on `Concept` would be a second copy of
  the same edge and reintroduce the exact one-sided-update drift we removed by
  decoupling false friends. So membership lives only on `Sense` in persistence, and
  `concept.lemmas` returns as a computed/hydrated view in the representation layer
  (phase 4). Synonym/dialect groups (`len(lemmas[lang]) > 1`) and cross-language
  cognate sets (multiple language keys) are read off that view, not a stored field.
- `id` is supplied (not computed) since it is built from the OMW source key at
  ingestion via `concept_id()`; validate it matches the `c__{slug}__{hash}` shape.

### `sense.py` (new) - `Sense` (the promoted edge, confirmed)

- Confirmed: the explicit `Sense` edge is in (the per-sense metadata - frequency,
  CEFR, later provenance/examples - makes the richer edge worth it). `Sense` is the
  **canonical membership record** for lemma <-> concept: the one place that
  relationship is stored.
- Persisted shape: `lemma_id: str`, `concept_id: str`; per-sense signals populated
  later: `token_frequency: float | None`, `sense_frequency: float | None`,
  `frequency_is_estimated: bool = False`, `cefr_level: str | None`,
  `cefr_is_estimated: bool = False`.
- Computed `id` via `sense_id(self.lemma_id, self.concept_id)`.
- Docstring notes frequency (phase 6) and CEFR (phase 6) land here, not on
  `Lemma`; the brainstorm's "bank" polysemy trap is the rationale.
- The hydrated accessors `sense.lemma -> Lemma` and `sense.concept -> Concept` are
  representation-layer conveniences (phase 4), not persisted fields - see below.

### `relations.py` (new) - edge tables

- `FalseFriendRelation`: `lemma_id_a`, `lemma_id_b`, `similarity_score: float |
  None`, `explanation_notes: dict[str, str]`, with a `model_validator(mode=
  "after")` enforcing canonical orientation (`lemma_id_a < lemma_id_b`) so each
  symmetric pair is stored once and dedups on ingestion.
- `ConceptRelation` (stub, populated phase 7): `concept_id_a`, `concept_id_b`,
  `relation_type: str` (`"hypernym"` directional, `"meronym"`, symmetric
  `"related"`, ...). Directional types keep source/target order; symmetric types
  reuse the canonical-ordering trick. Antonymy stays lemma-level (a future
  sibling of `FalseFriendRelation`), not here - documented in the docstring.

### `concept_id.py` / `sense_id.py` (new) - id constructors

- `concept_id(slug: str, source_key: str) -> str`: returns
  `c__{slug}__{hash[:12]}`, where `hash` is sha1 over `source_key` (the stable OMW
  synset/ILI key) so regeneration is deterministic and slug edits do not change
  the id. `sense_id` does not need the readable slug.
- `sense_id(lemma_id: str, concept_id: str) -> str`: deterministic hash of the
  ordered pair (the edge is identified by its endpoints).
- Document the **slug-dedup discipline**: two distinct concepts can derive the
  same human slug; the `hash[:12]` suffix keeps ids unique, and the ingestion
  pass (phase 5) is where colliding slugs are disambiguated for readability. Mirror
  `lemma_id.py`'s bare-hex, language-agnostic style.

### `__init__.py` - public surface

- Export `Concept`, `Sense`, `FalseFriendRelation`, `ConceptRelation`,
  `concept_id`, `sense_id`. Remove `FalseFriend`, `Gloss`, `GlossExample`,
  `FrequencyLevel` from `__all__` and imports. Update the module docstring.

### Keep the suite green (minimal call-site updates)

- **`ingestion/csv_loader.py`, `static_list.py`, `wiktionary.py`, `dedup.py`**:
  stop reading/writing the dropped fields; construct the thin `Lemma`. Unknown CSV
  columns are ignored (sample data is disposable per the no-migration decision).
- **`lemma_store.py`**: still loads the thin `Lemma`; no concept/sense registries
  yet (phase 4). Confirm `_LEMMAS_BY_ID` and the `get_*` helpers still work.
- **`webapp/routers/lemmas_router.py`**: the lemma payload loses the dropped
  fields; confirm the handlers and response shape still serialize.
- **Existing tests** (`tests/lexicon/test_lemma.py`, ingestion tests,
  `tests/webapp/test_lemmas_api.py`): drop assertions on removed fields; keep the
  normalized / id / computed-property coverage.

### New unit tests (`tests/lexicon/`)

- `test_concept_id.py`: `concept_id` determinism (same `source_key` -> same id),
  shape (`c__{slug}__{12 hex}`), and that slug changes do not change the id.
- `test_sense_id.py` / `test_sense.py`: `sense_id` determinism; `Sense.id`
  stable across instances; default per-sense fields are `None`/`False`.
- `test_relations.py`: `FalseFriendRelation` canonical reordering (a>b swaps),
  pair uniqueness; `ConceptRelation` directional vs symmetric handling.
- `test_concept.py`: round-trip `model_dump()` / re-parse for `Concept`, `Sense`,
  both edges; synonym group and multi-language cognate set shapes.

## Persistence vs representation

Two layers, kept deliberately separate so the on-disk source of truth stays thin
and drift-free while the Python objects stay ergonomic.

- **Persistence (on disk, source of truth).** Pure id-only records: `Lemma`
  (`text`/`language`/...), `Concept` (`id` + `definitions`), `Sense`
  (`lemma_id`/`concept_id` + per-sense fields), `FalseFriendRelation`,
  `ConceptRelation`. No object back-references and no derivable membership
  (`Lemma.concept_ids` and `Concept.lemmas` both omitted). These are exactly what
  `model_dump()` writes and what the round-trip unit tests cover. Each edge is
  stored once, in one place.
- **Representation (in memory, ergonomics).** After the store loads the records
  (phase 4), callers should be able to navigate objects directly:
  `sense.lemma -> Lemma`, `sense.concept -> Concept`, `lemma.senses -> list[Sense]`,
  `concept.senses -> list[Sense]`, and the computed `concept.lemmas` grouping. This
  removes the manual `get_lemma_by_id(sense.lemma_id)` hop the user called out.

Mechanism (recommended, implemented in phase 4): hold the back-references as
**store-hydrated optional fields excluded from serialization** -
`lemma: Lemma | None = Field(default=None, exclude=True, repr=False)` on `Sense`,
etc. The store sets them once at load time; `exclude=True` keeps them out of
`model_dump()` so the persisted shape is unaffected, and there is a single owner
(the store) so no drift. Computed groupings like `concept.lemmas` are derived,
not stored.

- *Alternatives considered*: (a) lazy `@property` accessors that call the store on
  each access - keeps fields out entirely but couples the model module to the store
  (lazy import to dodge the cycle) and recomputes on every access; (b) separate
  hydrated "view" classes distinct from the persisted DTOs - cleanest separation
  but doubles the class count and needs mapping code. The excluded-field approach
  is the least machinery for the same ergonomics and is the lean.
- Phase 2 only defines the persisted models and records this pattern; the
  excluded fields, the store wiring that populates them, and their tests are
  phase 4. Phase 2's round-trip tests assert `model_dump()` carries no back-refs.

## Decisions

All confirmed (2026-06-16):

- **Promote the explicit `Sense` edge, and drop `Lemma.concept_ids`.** The
  per-sense metadata (frequency, CEFR, later provenance/examples) makes the richer
  edge worth it; `Sense` is the single source of truth for membership, so `Lemma`
  carries no `concept_ids`. Supersedes the scope sketch's "add `concept_ids`".
- **Drop `Concept.lemmas`.** Redundant once `Sense` exists (rebuildable from the
  sense set + each lemma's language); returns as a computed representation-layer
  view, not a persisted field. See the analysis in `concept.py` above.
- **Glosses move entirely to `Concept`; `Lemma` keeps no glosses.** Canonical
  glosses live in `Concept.definitions`. Raw source glosses are *not* kept on
  `Lemma` as provenance; if provenance is wanted later it is reintroduced in the
  ingestion phase (5) where it is actually produced, not carried as an empty field
  now.
- **Concept slug source: OMW/ILI key first, else English gloss.** Derive the slug
  from the OMW/ILI synset key when present, falling back to the English gloss;
  finalized in ingestion (phase 5). The `concept_id` signature takes a pre-computed
  slug, so this phase stays agnostic to the source.

## Out of scope

- Concept/sense/edge registries and look-aside indexes (phase 4); the on-disk
  storage-format choice (phase 3); ingestion that fills the models (phase 5);
  frequency/CEFR population (phase 6) and relation population (phase 7);
  regenerating sample data and the `lang-tutor` consumer uplift (phase 9).

## Done when

- `Lemma` is thin; `Concept`, `Sense`, `FalseFriendRelation`, `ConceptRelation`
  and the `concept_id` / `sense_id` constructors exist with Google-style
  docstrings and validators.
- New unit tests cover id determinism, canonical edge ordering, and round-trip
  serialization; existing tests are updated to the thin `Lemma`.
- `uv run pytest && uv run ruff check . && uv run pyright` passes in `lang-tools`.
- Docs updated (`docs/library/lexicon.md` reflects the new models); the tracking
  Log records the phase and the confirmed decisions.
