---
status: planned
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

## Decisions to confirm

Recommendations given; each changes what gets built.

1. **Read `hyponym` as well as `hypernym`** and normalize to one direction.
   Recommend **yes**: it recovers ~10k edges per non-English lexicon that are otherwise
   invisible, and the graph is the backbone every other signal leans on.
   **This has a blast radius worth stating up front:** hypernym depth feeds phase 6's CEFR
   score, so a denser taxonomy moves the bands, and phase 6's Kelly validation has to be
   re-run and the cutoffs likely re-fitted. That is the cost of the fix, and it argues for
   doing it now rather than after more phases lean on the bands.
2. **Antonymy: store sense-level *and* derive concept-level.**
   Recommend both. Sense-level is what the source actually says; the derived concept edge
   is the only way pt/es/fr/it get opposites at all, and it is the same propagation
   argument phase 6 already validated for commonness. The alternative - English-only
   antonymy - makes the feature useless in four of five languages.
3. **Which synset types ship.** Recommend hypernym (+ hyponym-derived), `instance_hypernym`,
   `similar`, the three mero/holo pairs, `also`, `entails`, `causes`, `attribute`.
   Defer `domain_*` / `exemplifies` (topic metadata, better served by phase 8's topics) and
   **defer `derivation`** (74,708 edges, English-only, morphological rather than semantic,
   and no consumer asks for word families yet).
4. **Keep depth reading `hypernym` only**, excluding `instance_hypernym`.
   Recommend yes: "Rome is an instance of city" is not the same claim as "a city is a kind
   of settlement", and mixing them would deepen every proper noun by one for no semantic
   reason. It also bounds decision 1's effect on phase 6 to genuine taxonomy.
5. **No persisted degree metric.** 5.54 asked for connectivity "for the phase-6 ranking",
   and phase 6 shipped without needing it. Recommend computing it if and when a consumer
   appears, on the same reasoning phase 6 recorded for depth - and note that unlike depth,
   degree *is* a bounded adjacency count the store can answer at query time.

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

## Done when

- [ ] The wanted synset relation types are stored as normalized `ConceptRelation` edges,
      with both link directions read.
- [ ] Antonymy is stored sense-level and derived to concept-level, and a Portuguese lemma
      can reach an opposite.
- [ ] The gate carries the new invariants and reports per-type edge counts.
- [ ] Phase 6's bands are re-validated after the depth change, with the numbers recorded.
- [ ] `uv run pytest && uv run ruff check . && uv run pyright` green; docs + tracking
      updated.
