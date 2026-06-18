# Metadata catalog: OMW/`wn` and kaikki fields

Companion to [`../05.4_data_quality.md`](../05.4_data_quality.md). Full inventory of
what each source exposes, what the current pipeline **keeps**, what it **drops**, and
what is worth **promoting** into the final dataset in a later phase. Status legend:

- **kept** - flows into the persisted models today.
- **dropped** - read by `wn`/kaikki but not carried into our tables.
- **promote?** - a drop worth reconsidering (which phase would own it in parens).

## OMW via `wn` (the concept backbone)

`wn` exposes a richer graph than `wn_synset_entries` flattens into `SynsetEntry`. The
flatten currently keeps only `synset.id`, `ili`, `definition()`, `lemmas()`, `pos`.

### Synset level (`wn.Synset`)

| Field / method | Status | Notes |
| --- | --- | --- |
| `synset.id` | **kept** | lexicon-local synset id; the fallback grouping key |
| `synset.ili` | **kept** | ILI id string (e.g. `i35545`); the cross-lingual grouping key |
| `synset.definition()` | **kept** | the per-language gloss -> `Concept.definitions` |
| `synset.lemmas()` | **kept** | member surface forms -> `Lemma` rows |
| `synset.pos` | **kept** | single-letter POS -> `Lemma.part_of_speech` |
| `synset.examples()` | **dropped** | **promote? (phase 6/8)** - synset-level example sentences; would seed `Concept`/`Lemma` examples without kaikki's CC-BY-SA |
| `synset.hypernyms()` / `hyponyms()` | **dropped** | **promote? (phase 7)** - the is-a backbone; `ConceptRelation` stub already waits for it |
| `synset.meronyms()` / `holonyms()` | **dropped** | **promote? (phase 7)** - part-of relations |
| `synset.relations(...)` (similar, also_see, entails, causes, attribute, domain) | **dropped** | **promote? (phase 7)** - the rest of the typed concept graph |
| `synset.lexfile` / lexicographer file | **dropped** | coarse semantic category (`noun.person`, `verb.motion`); cheap **promote? (phase 6/8)** signal for clustering/difficulty |
| `synset.ili.definition()` (CILI English gloss) | **dropped** | a *language-independent* English gloss; useful canonical fallback when a language gloss is missing (phase 8) |
| `synset.metadata()` | **dropped** | source/confidence notes where a wordnet provides them |

### Sense / word level (`wn.Sense`, `wn.Word`)

`wn` has its own `Sense` and `Word` objects (distinct from our `Sense` edge). We read
only the bare lemma strings; everything else is dropped.

| Field / method | Status | Notes |
| --- | --- | --- |
| `sense.id` / sense key | **dropped** | **promote? (phase 6)** - stable per-sense key; the join key for SemCor `tag_count` sense frequencies |
| `sense.counts()` (`tag_count`) | **dropped** | **promote? (phase 6)** - SemCor sense-tag counts; the weight for splitting token frequency across senses (English mainly) |
| `sense.relations()` (antonym, derivation, pertainym, ...) | **dropped** | **promote? (phase 7)** - antonymy is **lemma/sense-level** in WordNet, so it lands on a sibling of `FalseFriendRelation`, not `ConceptRelation` |
| `word.forms()` / inflected forms | **dropped** | morphology; out of scope for the meaning dataset |
| `word.pos`, `word.lemma()` | partially **kept** | lemma string kept; per-word POS is the synset POS we already use |
| lexical/syntactic frames, pronunciations | **dropped** | not in `wn` for OMW 1.4 lexicons in practice |

### Lexicon level

| Field | Status | Notes |
| --- | --- | --- |
| lexicon id / version / `lang` | **kept (in manifest)** | `_build.json` pins lexicon specifiers + versions |
| lexicon **license** | **dropped** | **promote? (phase 10)** - per-wordnet, and *not uniformly Apache-2.0*. OMW members carry different licenses (CC-BY, MIT, wordnet license, ...). The brainstorm's "OMW is Apache-2.0" is too broad: **verify per lexicon** (en/pt/es/fr/it each) for the dataset card |

### Note on POS codes

`_POS_LABELS` maps `n/v/a/s/r` -> noun/verb/adjective(+satellite)/adverb. `wn` may also
surface `p` (adposition), `x` (other), `u` (unknown) for some lexicons - currently these
map to `None`. Worth counting (check 4) so an unmapped POS does not silently become a
null.

## kaikki.org (wiktextract) - the enrichment layer

> **Decided (2026-06-18): drop kaikki entirely.** The first full build showed its
> sense-blind join yields low-quality non-en glosses (the `house` mess) and pulls
> CC-BY-SA over ~53% of concept glosses, while contributing nothing to what we need (a
> good English gloss + concept grouping, both from OMW/ILI). Examples, if wanted, come
> from Tatoeba (CC-BY). See [`../05.4_data_quality.md`](../05.4_data_quality.md),
> "emerging direction" (1). The inventory below documents what kaikki *would* have
> provided, for the record.

A kaikki JSONL line is far richer than `WikiRecord`/`KaikkiEntry` parse. `WikiRecord`
sets `extra="ignore"`, so **every unlisted field is silently dropped**. What we keep:
the first gloss per missing language (`Concept.definitions`) and example sentences
(`Lemma.examples`).

### Currently parsed (in `WikiRecord` / `WikiSense`)

| Field | Status | Notes |
| --- | --- | --- |
| `word` | **kept** | headword; the join key with `language` |
| `pos` | parsed, **dropped in concept path** | finer than OMW (`intj`, `phrase`, `expression`); **promote? (phase 8)** as a POS cross-check / review signal |
| `senses[].glosses` | **kept (first, when OMW blank)** | only the first gloss of the matched headword reaches a concept - the `house` defect's mechanism |
| `senses[].examples` | **kept** | `{text, english/translation}` -> `LemmaExample` |
| `senses[].raw_glosses` | parsed, **dropped** | uncleaned gloss; rarely needed |
| `senses[].tags` | parsed, **dropped** | **promote? (phase 6/8)** - `archaic`, `colloquial`, `transitive`, register/usage labels: directly useful for difficulty + filtering |
| `senses[].topics` | parsed, **dropped** | **promote? (phase 8)** - subject domains -> `Lemma.topics` (the field exists, unfilled) |
| `senses[].categories`, top-level `categories` | parsed, **dropped** | Wiktionary maintenance categories; mostly noise |
| `form_of` | parsed, used as a **filter only** | marks inflected forms (used to skip them in `load_wiktionary_jsonl`) |

### Present in kaikki JSONL but not parsed at all (dropped via `extra="ignore"`)

| Field | Status | Notes |
| --- | --- | --- |
| `translations` | **dropped** | **promote? (phase 8)** - explicit cross-lingual links; a sense-blind but useful signal to validate or seed ILI-orphan grouping. CC-BY-SA |
| `sounds` (IPA, audio) | **dropped** | pronunciation; possible future `lang-tutor` use, not this dataset |
| `etymology_text` / `etymology_templates` | **dropped** | etymology; could support cognate/false-friend detection (phase 7), low priority |
| `synonyms`, `antonyms`, `hypernyms`, `hyponyms`, `derived`, `related`, `coordinate_terms` | **dropped** | **promote? (phase 7)** - lemma-level relation lists; cross-check / fill for the OMW relation graph. CC-BY-SA |
| `forms` (inflection table) | **dropped** | morphology; out of scope |
| `wikipedia` / `wikidata` sense links | **dropped** | **promote? (phase 8)** - a bridge to Wikidata Lexemes / Wikipedia for disambiguation |
| `senses[].id`, `senses[].links`, `senses[].qualifier` | **dropped** | sense-level provenance; not needed yet |
| `lang` / `lang_code` | **kept (we stamp our own)** | we pass the ISO code in rather than trust the dump's |

### License reminder

Everything kaikki contributes is **CC-BY-SA 3.0/4.0** (share-alike). Any promoted kaikki
field stays `source=kaikki` and license-isolated; promoting more kaikki content raises
the share-alike surface the phase-10 license decision must cover. Glosses/translations
are the share-alike-sensitive text; an LLM-rewrite path (brainstorm option c) is the way
to use kaikki as *guidance* without inheriting the license.

## Quick "promote shortlist" (for later phases)

Highest value, lowest cost first:

1. **`synset.examples()`** (OMW, permissive) - examples without the CC-BY-SA tax. *(6/8)*
2. **`synset.hypernyms/hyponyms` + `sense` antonyms** - the relation graph the stubs
   already expect. *(7)*
3. **`sense.counts()` / `tag_count` + sense keys** - the only real per-sense frequency
   signal. *(6)*
4. **`lexfile` / lexicographer category** - free coarse semantic class for clustering /
   difficulty. *(6/8)*
5. **kaikki `tags` + `topics`** - register/domain labels; `Lemma.topics` already exists.
   *(8)*
6. **per-lexicon license strings** - required for an honest dataset card. *(10)*
