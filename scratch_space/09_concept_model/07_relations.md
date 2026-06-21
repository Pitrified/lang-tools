---
status: draft
---

# Phase 7 - semantic relations

> Draft. Scope sketch to hold the overarching story; not yet the plan of record.

## Overview

Populate the typed edges beyond false friends - hypernymy/hyponymy and antonymy -
using the generic edge tables stubbed in phase 2 and the relation data OMW
already carries. Kept deliberately small for the first cut; the concept layer
stays flat (sense grouping) and these edges sit beside it. Context:
[`00-concepts-brainstorm.md`](00-concepts-brainstorm.md), "Semantic relations
beyond false friends". May fold into phase 5 (ingestion) since OMW supplies the
edges in the same traversal.

> **From the 5.5 cleanup (2026-06-20).** Step 4 of
> [`05.5_cleanup.md`](05.5_cleanup.md) captures `synset.hypernyms/hyponyms` and sense
> `antonyms` during the kaikki-free rebuild, in the same OMW traversal - so the edges this
> phase needs are already emitted by the cleanup build. This phase then types, stores, and
> prunes them. This reinforces the "may fold into phase 5" note above.

> **From the 5.54 exploration (2026-06-21).** The relations notebook
> ([`notebooks/lexicon_enrich/04_relations`](../../notebooks/lexicon_enrich/)) measured the
> graph `wn` actually exposes for our lexicons:
> - **Synset-level (concept-level) edges are dense and ILI-keyed**, so they resolve directly
>   onto the ILI-grouped concepts the build produces - no per-language replication needed.
>   hypernym / hyponym dominate (89,089 edges each), then holonym / meronym (member / part /
>   substance), `similar` (23,134), domain links, `also`, `entails`, `causes`. Hypernym /
>   hyponym are the cheap, dense first cut; holonym / meronym / similar are nearly free to add
>   in the same traversal.
> - **Antonym and derivation are sense-level, not synset-level** (derivation 74,708, antonym
>   7,979, pertainym 8,023). Read them off `sense.relations()`, then resolve to the senses'
>   concepts - confirming antonymy belongs on the symmetric lemma/sense edge table, not
>   `ConceptRelation`.
> - **Connectivity is a usable ranking signal**: only 7% of synsets are isolated (degree 0),
>   so a degree metric is meaningful across the graph - expose it to the phase-6 ranking.

## What this phase will cover

- **Hypernymy / hyponymy (is-a)** - the WordNet backbone. Directional, stored on
  `ConceptRelation` as `(parent_concept_id, child_concept_id)` with
  `relation_type="hypernym"`; no canonical reordering. Powers category drills and
  difficulty grading (more specific tends to be rarer/harder).
- **Antonymy (opposites)** - a *lemma*-level relation in WordNet, so stored on a
  symmetric lemma/sense edge table parallel to `FalseFriendRelation`, not on
  `ConceptRelation`. Powers opposite-matching exercises and distractors.
- **Meronymy (part-of)** and other WordNet relations - lower priority but nearly
  free to capture in the same synset traversal (5.54 Topic 4: holonym / meronym /
  `similar` are already present and ILI-keyed); confirm the generic
  `ConceptRelation` model does not preclude adding them later.
- **Connectivity metric** - emit a per-concept degree from the synset graph (only
  7% isolated) for the phase-6 ranking.
- **Ingestion hook** - extend the phase-5 OMW pass (via `wn`) to emit the chosen
  relation types; hypernym / hyponym come from `synset.relations()`, antonym from
  `sense.relations()` (5.54 Topic 4). Choose which types to import and at what depth.

## Open points to resolve here

- Which relation types ship in the first cut (hypernymy + antonymy proposed;
  holonym / meronym / similar are cheap add-ons per 5.54 Topic 4).
- Traversal depth / pruning so the edge tables stay LFS-friendly (tie back to
  phase 3).

## Out of scope

- A hierarchical "concept cluster" layer above synsets (only if granularity from
  phase 5 proves too fine); exposing relations in exercises (`lang-tutor`).

## Done when (draft)

- Hypernymy and antonymy edges loaded and queryable via the phase-4 store over the
  five languages; adjacency lookups covered by tests.
- `uv run pytest && uv run ruff check . && uv run pyright` passes.
