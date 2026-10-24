---
status: done
---

# Phase 7 - semantic relations

Populate the typed edges beyond hypernymy: the rest of the synset graph OMW already
carries, plus antonymy, which lives at a different granularity and needs its own home.
Phase 5.5 Step 4 already emits hypernym edges, so this phase is not "start relations" -
it is **finish** them, and fix what the first cut got wrong.

Context: [`00-concepts-brainstorm.md`](00-concepts-brainstorm.md), "Semantic relations
beyond false friends"; the edge models are the phase-2 stubs.

## Inherited decisions

> **From 5.5 (2026-06-20).** `synset.hypernyms` is captured in the kaikki-free rebuild's
> OMW traversal, so the backbone edges already exist (97,666 in the shipped corpus). This
> phase types, extends and prunes them.

> **From the 5.54 exploration (2026-06-21).**
> - Synset-level edges are dense and **ILI-keyed**, so they resolve straight onto the
>   ILI-grouped concepts - no per-language replication needed.
> - **Antonym and derivation are sense-level, not synset-level**, so they are read off
>   `sense.relations()`; antonymy does not belong on `ConceptRelation`.
> - Only ~6-7% of synsets are isolated, so a degree metric is meaningful.

## Measurements taken while planning (2026-09-02)

> **Superseded by the [Result](#result-2026-10-21).** Finding 1 below was an artifact of
> `wn`'s lexicon *expansion*: the non-English wordnets carry no relations of their own, and
> what was counted here was English's graph projected onto them. No taxonomy was being
> dropped. Kept as the record of what the plan was built on.

Surveyed every relation type `wn` exposes across all five installed lexicons, not just
English (5.54's numbers were English-only). Two results change the design.

### 1. Hyponym is redundant in English and *not* in the others

The build reads `hypernyms` only, on the reasoning recorded in `RELATION_HYPERNYM`:
"hyponymy is the same edge read backwards, so it is never stored separately". That is
sound as a **storage** rule and was silently applied as a **reading** rule, which the
non-English wordnets do not support:

| lexicon | edges from `hypernym` | edges from `hyponym` (reversed) | union | only in `hyponym` |
| --- | --- | --- | --- | --- |
| en | 89,089 | 89,089 | 89,090 | 1 |
| pt | 32,680 | 33,944 | 42,807 | 10,127 |
| it | 29,538 | 32,655 | 39,824 | 10,286 |

English mirrors its links perfectly; pt and it do not, so **the current build drops around
a quarter of the taxonomy available in each non-English lexicon** (pt +31%, it +35% if both
directions are read). Nothing about this is visible without reading both, which is why it
survived 5.5 and 5.54.

### 2. Sense-level relations exist only in English

| lexicon | synset relation types | sense relation types |
| --- | --- | --- |
| en | 21 (hypernym/hyponym 89,089, similar 23,134, holo/mero_member 12,293, mero/holo_part 9,097, instance_hypernym 8,577, domain_topic 6,643, also 2,692, attribute 1,278, exemplifies 967, mero/holo_substance 797, entails 408, causes 220) | derivation 74,708, pertainym 8,023, **antonym 7,979**, also 580 |
| pt / es / fr / it | the same 21 types, 30k-65k edges each | **none at all** |

So antonymy is English-only, exactly like the SemCor counts phase 6 dealt with - and the
same propagation question follows.

## Shape

Three changes, each small on its own.

**1. `SynsetEntry.relations`, one field instead of one per type.** `hypernyms:
tuple[str, ...]` becomes `relations: dict[str, tuple[str, ...]]` (type -> target synset
ids), and `_hypernym_edges` generalizes to `_relation_edges`, which walks the wanted types
and resolves both endpoints through the existing `key_to_cid` map. Inverse pairs
(`hyponym` -> `hypernym`, `holo_*` -> `mero_*`, `instance_hyponym` -> `instance_hypernym`)
are normalized to one stored direction on read, which is what makes finding 1 a fix rather
than a doubling of the table.

**2. A `sense_relations` table** - the sibling `relations.py` already anticipates
("antonymy is a lemma-level relation and will arrive as a future sibling of
`FalseFriendRelation`"). It stores `(sense_id_a, sense_id_b, relation_type)`, symmetric
and canonically ordered. Note the correction to the phase-2 note: **sense-level, not
lemma-level.** WordNet's antonymy is between word senses, and collapsing it to lemmas
would assert that `light` is the opposite of `heavy` in its illumination sense. The
endpoints are the existing computed `Sense.id`s, so nothing new has to be minted.

**3. Derived concept-level antonymy.** English sense antonymy implies its two *concepts*
are opposed, and concepts are shared across languages, so the derived edge gives Italian
and Portuguese opposites they otherwise cannot have. Emitted as `ConceptRelation` with
`relation_type="antonym"` (symmetric), tagged so the derivation is visible.

## Decisions (settled 2026-10-21)

All five were put to the user as recommendations; each was confirmed as recommended.

1. **Read `hyponym` as well as `hypernym`, normalized to one stored direction** - confirmed.
   Recovers the non-English taxonomy the build silently dropped. The cost is accepted
   up front: hypernym depth feeds phase 6's CEFR score, so Kelly validation re-runs in
   Step 6 and `CEFR_CUTOFFS` is re-fitted if the bands moved. The losing option ("store the
   recovered edges but freeze depth on the old reading") was rejected because it leaves two
   notions of "the taxonomy" in one build.
   **Widened by the execution-time survey (below):** the same normalization applies to
   every inverse pair, not only hypernymy - outside English, the mero/holo pairs and
   `instance_hypernym` are just as incompletely mirrored.
2. **Antonymy: sense-level table *and* derived concept-level edges** - confirmed. The
   `sense_relations` table records what the source says (English sense pairs); the derived
   `ConceptRelation(antonym)` edges are what give pt/es/fr/it opposites at all. Derived
   rows carry the provenance tag `derived`, so the derivation stays visible on disk. The
   losing options were sense-only (antonymy useless in four of five languages) and
   concept-only (loses which English senses the source opposed).
3. **Shipped synset types: the plan's list** - confirmed: `hypernym` (+ hyponym),
   `instance_hypernym` (+ instance_hyponym), `mero_member` / `mero_part` / `mero_substance`
   (+ their `holo_*` inverses), `similar`, `also`, `attribute`, `entails`, `causes`.
   Deferred: `domain_*` / `exemplifies` (topic metadata, phase 8) and `derivation` /
   `pertainym` (English-only morphology, no consumer).
4. **Depth reads `hypernym` only, excluding `instance_hypernym`** - confirmed. Already
   true of `enrich.hypernym_depths`, which filters on `RELATION_HYPERNYM`; keeping
   `instance_hypernym` a distinct type is what preserves it.
5. **No persisted degree metric** - taken as recommended (computable at query time if a
   consumer appears).

## Execution-time survey (2026-10-21)

> **Also superseded by the [Result](#result-2026-10-21)** for the same reason: the
> non-English rows of the first table are projections of English through the ILI, not
> links those wordnets state. The direction semantics and the Step-6 baseline below stand.

Re-run on the fresh rebuild before writing code, across all five lexicons and every pair
the shipped list touches (raw `wn` link counts, de-duplicated as `(source, target)` pairs).

Directional inverse pairs - edges that exist **only** on the inverse side:

| pair (stored <- inverse) | en | pt | es | fr | it |
| --- | --- | --- | --- | --- | --- |
| `hypernym` <- `hyponym` | 1 | 10,127 | 8,447 | 10,462 | 10,286 |
| `instance_hypernym` <- `instance_hyponym` | 0 | 404 | 368 | 391 | 612 |
| `mero_member` <- `holo_member` | 0 | 1,452 | 2,004 | 1,211 | 1,923 |
| `mero_part` <- `holo_part` | 0 | 620 | 1,019 | 598 | 720 |
| `mero_substance` <- `holo_substance` | 0 | 116 | 108 | 118 | 128 |

`entails` and `causes` have no inverse type in any lexicon (`is_entailed_by` /
`is_caused_by` never appear), so they are read as-is. The symmetric types are perfectly
mirrored in English and not elsewhere (`similar` has 2,374 unmirrored pt links of 6,942;
`also` and `attribute` about 30% / 25%), which is what canonical `a < b` ordering fixes.
English sense antonymy: 7,979 directed links, 5 unmirrored, so it is symmetric too.

Direction semantics, checked on known synsets so the stored orientation is documented
rather than assumed: `car mero_part accelerator` (a = whole, b = part), `Rome holo_part
Italy` (the inverse), `buy entails pay`, `kill causes die`, `Rome instance_hypernym
national capital`, and `hot attribute temperature` / `hot` sense `antonym` `cold`.

Phase 6 baseline for Step 6, reproduced on the fresh rebuild before any change: en
41.2% exact / 74.4% within one band / Spearman 0.632; it Spearman 0.661 and mean offset
+1.23 - matching the numbers phase 6 recorded. One thing the reproduction surfaced:
`fit_cutoffs` on today's corpus does not return the shipped `CEFR_CUTOFFS` (first cutoff
0.2956 vs 0.2774; the shipped set leaves an en mean offset of +0.17 that a true fit would
not), so the shipped cutoffs were fitted on an earlier state of the scores. Step 6 re-fits
on the final phase-7 corpus either way.

## Steps

1. **`SynsetEntry.relations`** replaces `hypernyms`; `wn_synset_entries` fills it from
   `synset.relations()`. Unit tests over fakes.
2. **`_relation_edges`** with the inverse-type normalization table and the wanted-type
   allowlist; dangling targets stay counted-and-dropped, never half-emitted.
3. **`sense_relations` table**: model, codec schema + partitioning decision, store
   registry, `TABLES`, `CACHE_VERSION` bump, `sense_relations_for(sense_id)` query.
4. **Antonym extraction** from `sense.relations()` in the OMW reader, resolved to our sense
   ids in `group_to_records`, plus the derived concept-level edges.
5. **Rebuild + re-gate**; new invariants (below); `report.md` regenerated.
6. **Re-validate phase 6** against Kelly and re-fit `CEFR_CUTOFFS` if the depth change moved
   them; record the before/after in
   [`06_frequency_complexity.md`](06_frequency_complexity.md).
7. **Webapp**: the existing `/concepts/{id}/relations` endpoint already filters by type, so
   it needs no change; add the sense-relation read only if a consumer asks.
8. `uv run pytest && uv run ruff check . && uv run pyright`; docs + tracking updated.

## Gate additions

- every `ConceptRelation.relation_type` and `sense_relations.relation_type` is in the
  known-type allowlist (an unrecognized type means the reader let a new OMW type through
  unreviewed);
- no relation table holds both `(a, b)` and `(b, a)` for a directional type - the
  normalization is the whole point of decision 1;
- dangling endpoints stay 0 (the existing invariant already covers `concept_relations`;
  extend it to `sense_relations`);
- edge counts per type are reported, so a re-ingestion that silently loses a type is
  visible in the diff.

## Out of scope

- `derivation` and `pertainym` (deferred above), and any morphological word-family feature.
- A hierarchical concept-cluster layer above synsets.
- False-friend population - still phase 7's neighbour, not its content: no source supplies
  them, so they stay an LLM/curation job for phase 8.
- Exposing relations in exercises (`lang-tutor`, phase 9).

## Result (2026-10-21)

Built and gated on the five-language corpus; all **ten** invariants pass (the eight carried
over plus the two added here). Concepts, lemmas, senses and every CEFR band count are
unchanged; the relation graph is what moved.

| table | type | edges |
| --- | --- | --- |
| `concept_relations` | `hypernym` | 89,089 |
| | `mero_member` / `mero_part` / `mero_substance` | 12,293 / 9,097 / 797 |
| | `similar` / `also` / `attribute` | 11,567 / 1,447 / 639 |
| | `instance_hypernym` | 8,577 |
| | `antonym` (provenance `derived`) | 3,802 |
| | `entails` / `causes` | 408 / 220 |
| | **total** | **137,936** (was 97,666) |
| `sense_relations` | `antonym` | 3,992 |

Lemmas that can now reach an opposite through a concept `antonym` edge: en 9,612, it
6,225, pt 4,244, fr 4,066, es 3,255 - against none outside English before. pt `quente` ->
`frio`, es `feliz` -> `triste`, it `alto` -> `basso`.

### What the plan had wrong, found by the build

1. **The non-English wordnets have no relations.** Opened with `expand=""`, omw-pt and
   omw-it report zero links of any type. By default `wn` lets a lexicon borrow another
   installed lexicon's relations through the ILI, so every "pt relation" the planning
   survey counted was English's graph seen through pt's partial coverage - which is why
   hypernym and hyponym looked unmirrored, and why the first real build logged ~250k
   targets that did not resolve. At the ILI level every projected edge was already in
   English's graph. So Decision 1's headline ("the build drops a quarter of the
   non-English taxonomy") was false, and so was the blast radius it warned about: there is
   no denser taxonomy for the bands to move on. Reading both names of every pair is still
   right and still shipped - it is the correct rule, and it costs nothing - but it recovers
   no edges on OMW 1.4. The reader now opens each wordnet with `expand=""`: the stored edges
   came out byte-identical to the expanded read, the dangling counts are real (0), and the
   build is ~40 s faster.
2. **The old `hypernym` edges included instance links.** `wn`'s `Synset.hypernyms()`
   returns instance hypernyms too: the 97,666 edges were 89,089 hypernym + 8,577
   instance_hypernym exactly. Decision 4 ("depth reads `hypernym` only") rested on the
   premise that the two had never been mixed; in fact phase 6's depth, and its fitted
   cutoffs, counted instance links all along. Excluding them would have made every
   instance concept a depth-0 root, which the score reads as maximally general (~1,640
   proper-noun senses leaving C2). **Decision 4 was revisited with the user** and reversed:
   depth walks both (`relations.TAXONOMY_RELATIONS`), the types stay separate in storage.
3. **Reading both directions surfaced one contradiction**, the WordNet 3.0 `restrain` /
   `inhibit` cycle: `restrain` lists `inhibit` as both its hypernym and its hyponym. The
   new orientation invariant caught it on the first gated build. A directional edge stated
   both ways now keeps the better-supported orientation (here `restrain -> inhibit`, stated
   twice against once) and a tie drops both; exactly one pair is resolved.

### Step 6 - phase 6 re-validated

Kelly validation on the final corpus is **identical** to the pre-phase-7 baseline (en
41.2% exact / 74.4% within one band / Spearman 0.632; it Spearman 0.661, offset +1.23), as
it must be with depth unchanged. No re-fit: the plan's re-fit condition ("if the depth
change moved them") did not occur. Still open, and deliberately not acted on here: the
shipped `CEFR_CUTOFFS` are not what `fit_cutoffs` returns on today's corpus (first cutoff
0.2774 shipped vs 0.2956 fitted; the shipped set leaves an en mean offset of +0.17 where a
true fit has 0). A re-fit would move bands, so it is a phase-6 decision to take on its own
rather than a side effect of this phase.

### Step 7 - webapp

No change: `/concepts/{id}/relations` already filters by `relation_type`, so the new types
are served as they are. No consumer asks for sense relations over HTTP yet, so
`sense_relations_for` stays a library read.

## Done when

- [x] The wanted synset relation types are stored as normalized `ConceptRelation` edges,
      with both link directions read.
- [x] Antonymy is stored sense-level and derived to concept-level, and a Portuguese lemma
      can reach an opposite.
- [x] The gate carries the new invariants and reports per-type edge counts.
- [x] Phase 6's bands are re-validated after the depth change, with the numbers recorded
      (identical: depth did not change, see Result).
- [x] `uv run pytest && uv run ruff check . && uv run pyright` green; docs + tracking
      updated.
