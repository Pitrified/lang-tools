# What we ingest: models, sources, meaning

Companion to [`../05.4_data_quality.md`](../05.4_data_quality.md). Explains the three
ingested models, where each field comes from, what it means, and the `house` defect.

## The three models (persisted shape)

All under `src/lang_tools/lexicon/`. Defined in phase 2
([`../02_core_models.md`](../02_core_models.md)); populated in phase 5
([`../05_ingestion.md`](../05_ingestion.md)). The persisted records are **thin and
id-only**; the ergonomic back-references (`sense.lemma`, `concept.lemmas`) are a
representation-layer concern hydrated by the store, not stored.

### `Concept` - the language-independent meaning

| Field | Source | Meaning |
| --- | --- | --- |
| `id` | built at ingestion: `concept_id(slug, source_key)` -> `c__{slug}__{hash[:12]}` | stable concept id. `source_key` is the **ILI key** (`ili::i35545`) when present, else `syn::{lang}::{synset_id}`. `slug` is `_pick_slug_source` (prefers an en lemma, then any lemma, then a gloss, else `"concept"`). |
| `definitions` | OMW synset gloss per language, topped up by kaikki for missing languages | `{"en": "...", "pt": "..."}`. **First non-empty gloss per language wins**; there is no per-sense definition - one string per language per concept. |

`Concept.lemmas` is **not stored** (derivable from the `Sense` set + each lemma's
language). Membership lives only on `Sense`.

### `Lemma` - the thin lexical token

| Field | Source | Meaning |
| --- | --- | --- |
| `text` | OMW synset member (`synset.lemmas()`), or kaikki headword | surface form, accents preserved |
| `language` | the ISO code we passed to `wn_synset_entries` | which wordnet supplied it |
| `normalized` | computed validator | accent/case-folded form; basis of `Lemma.id` |
| `part_of_speech` | OMW `synset.pos` mapped via `_POS_LABELS` (`n->noun`, `s->adjective`, ...) | **OMW-only in the concept path**; kaikki POS is parsed but not carried onto OMW lemmas |
| `examples` | **kaikki only** (`LemmaExample(sentence, translation)`) | example sentences; empty unless a kaikki headword matched |
| `sources` | `["omw"]`, appended `"kaikki"` if enriched | provenance list on the model |
| `topics` | currently unset by the OMW path | reserved (kaikki carries topics; not joined yet) |

`Lemma.id` = sha1 of `language::normalized` - so two synsets sharing a form yield **one**
lemma (dedup by id). No `concept_ids` field (the `Sense` edge is the single source of
truth).

### `Sense` - the lemma <-> concept edge (the membership record)

| Field | Source | Meaning |
| --- | --- | --- |
| `lemma_id`, `concept_id` | OMW synset membership | the edge: "this lemma expresses this concept" |
| `id` | `sense_id(lemma_id, concept_id)` | deterministic edge id |
| `token_frequency`, `sense_frequency`, `frequency_is_estimated` | **null today** (phase 6) | per-sense frequency |
| `cefr_level`, `cefr_is_estimated` | **null today** (phase 6) | per-sense difficulty |

Senses carry **no text**, so they are always `source=omw` and are the table to use for
all membership counting.

## Where definitions come from (and the `house` defect)

Pipeline ([`transform.py`](../../../src/lang_tools/lexicon/ingestion/transform.py)):

1. `group_to_records` builds each `Concept.definitions` from **OMW synset glosses**,
   one per language, first non-empty wins.
2. `_enrich_concepts` then fills a language **only if OMW left it blank**, using the
   kaikki entry of any of that concept's lemmas in that language, joined by
   `(normalized text, language)`. First kaikki gloss of that headword wins.

### Why `house` (the family sense) shows `es`/`pt` definition = "house"

The notebook spot-check picks the synset that means **house = a family/dynasty** (e.g.
"the House of Windsor"), which in en/pt/es shares an ILI, so it is one `Concept`. Two
things combine:

1. **OMW left the es/pt gloss blank** for that synset (gloss coverage is en-heavy and
   patchy for the dynasty sense), so step 2 tries kaikki.
2. **The kaikki join is lemma-level, not sense-level.** It looks up the Portuguese /
   Spanish headword that happens to be a member of that synset and takes its **first**
   gloss - but kaikki orders senses by frequency, so the *first* gloss is the common
   "building where people live" meaning, or, for a word like `casa`/Spanish `casa`, a
   short gloss that can literally read "house" (an English translation gloss). The
   definition that lands is therefore **the wrong sense** (the building, or a bare
   translation), not "noble family" - and it can be the single word `house`.

So "definition is just `house`" is two defects stacked:

- **sparse OMW glosses** outside English (measure: per-language gloss coverage), and
- **a sense-blind enrichment join** that attaches a lemma's *most common* gloss to
  whatever synset that lemma is a member of (measure: `definition == lemma` count, and
  definitions that are a single English word in a non-en language slot).

Neither is a transform *bug* - the join does exactly what it is coded to do - but both
are **quality** defects routed to phase 8 (gloss enrichment) and informing phase 5's
optional LLM granularity/mapping seam. The check `normalize(definition) ∈ lemma_forms`
in [`../05.4_data_quality.md`](../05.4_data_quality.md) quantifies exactly this.

## Can we trust the POS?

- POS on OMW lemmas is the **synset** POS (one POS for the whole synset), which is
  reliable *as a coarse class* but coarse: WordNet's `s` (satellite adjective) is folded
  into `adjective`, and OMW has no finer grammatical detail.
- The kaikki POS (`WikiRecord.pos`, finer: `intj`, `phrase`, `expression`, ...) is
  parsed but **discarded** in the concept path. So today POS = OMW POS, full stop.
- The useful trust signal is **agreement**: where a lemma is both an OMW member and a
  kaikki headword, compare the two POS. Disagreement flags a review candidate (e.g. a
  form OMW calls a noun that Wiktionary marks an interjection). That is a phase-8 review
  queue, not an auto-fix - quantified by check 4.
