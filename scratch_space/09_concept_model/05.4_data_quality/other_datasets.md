# Other datasets: metadata, access, fit

Companion to [`../05.4_data_quality.md`](../05.4_data_quality.md). Datasets beyond the
two we already ingest (OMW + kaikki), what metadata each carries, how to access it, and
where it would slot into the phase plan. Scoped to the five target languages
(en/pt/es/fr/it). The brainstorm already names some of these
([`../00-concepts-brainstorm.md`](../00-concepts-brainstorm.md), "Background",
"Frequency", "Complexity"); this consolidates them with current access details.

## Concept / sense inventories (could extend the backbone)

### CILI - Collaborative Interlingual Index

- **What**: the stable cross-lingual concept namespace OMW already links through; every
  ILI record has an English definition and a permanent id. It is the *index* behind the
  `ili::` keys we group on.
- **Metadata**: ILI id, English gloss, status, provenance, links to Princeton WordNet.
- **Access**: [globalwordnet/cili](https://github.com/globalwordnet/cili) (flat file);
  already reachable via `wn` (`synset.ili`). Open license.
- **Fit**: a **canonical English fallback gloss** for ILI-backed concepts whose language
  glosses are all sparse (directly mitigates the `house`-style empty-gloss case). *(8)*

### BabelNet

- **What**: the largest multilingual synset network (250+ languages), merging WordNet +
  Wikipedia/Wikidata + others under one cross-lingual sense id - exactly the model this
  project emulates.
- **Metadata**: BabelSynset id, multilingual senses, glosses, images, domains, relations,
  Wikipedia/Wikidata links, sense frequencies.
- **Access**: HTTP API (key, daily-capped free tier) + downloadable indices for research.
  [babelnet.org](https://babelnet.org/about). **License is restrictive** for
  redistribution - usable to *guide/validate* mapping, **not** to ship verbatim in an
  open dataset.
- **Fit**: validation oracle / mapping aid in phase 8, not a shipped source.

### Wikidata Lexemes

- **What**: structured Lexeme/Form/Sense entities, multilingual, **CC0** (public domain).
- **Metadata**: lexeme id, language, lemma, POS, forms (with grammatical features),
  senses with glosses (per language), and sense statements that can link to Wikidata
  items / other lexemes (derivation, translation).
- **Access**: SPARQL via the Wikidata Query Service, REST API, and full dumps.
  [Wikidata:Lexicographical data](https://www.wikidata.org/wiki/Wikidata:Lexicographical_data).
- **Fit**: the **only permissively-licensed (CC0)** multilingual sense source here - a
  clean alternative to CC-BY-SA kaikki for glosses/translations where coverage exists
  (coverage is still thin/uneven per language). Worth a coverage probe in phase 8.

### ConceptNet

- **What**: multilingual commonsense graph of words/phrases linked by typed edges
  (`/r/IsA`, `/r/PartOf`, `/r/RelatedTo`, `/r/Synonym`, ...). Concepts are surface terms
  per language, not synsets.
- **Metadata**: term URIs (`/c/{lang}/{term}`), relation URIs, weights, sources/datasets.
- **Access**: JSON-LD web API + bulk download.
  [conceptnet.io](https://conceptnet.io/). **CC-BY-SA 4.0** (share-alike).
- **Fit**: relation enrichment (phase 7) and `RelatedTo` for distractor generation; same
  share-alike caveat as kaikki. Note `wordfreq` is a sibling project (below).

### PanLex

- **What**: very wide translation graph (thousands of languages) keyed by "expressions"
  and "meanings"; breadth over depth, no rich glosses.
- **Metadata**: expression, language variety, meaning id, source attributions.
- **Access**: bulk DB download + API. CC0. Mentionable for breadth; low priority for five
  high-resource languages.

## Frequency sources (phase 6)

### wordfreq

- **What**: token frequency on the Zipf scale; the planned default (MIT-ish, see note).
  Combines Wikipedia, OpenSubtitles, news, web (Common Crawl), Reddit/Twitter, SUBTLEX,
  Leeds. All five target languages are well covered (each has >=3 sources).
- **Metadata**: per-word Zipf value (log10 per-billion), precise to ~1%.
- **Access**: `pip install wordfreq`; `zipf_frequency(word, lang)`.
  [wordfreq on PyPI](https://pypi.org/project/wordfreq/) /
  [rspeer/wordfreq](https://github.com/rspeer/wordfreq).
- **Caveat**: recent wordfreq releases are **frozen / no longer maintained** by the
  author and bundle data under mixed terms (some CC-BY-SA via ConceptNet's exquisite
  corpus). Pin a version and **license-check before shipping** (phase 10), do not assume
  pure MIT for the *data*.
- **Fit**: `Sense.token_frequency` (copied per sense), `Lemma`-level max aggregate.

### SUBTLEX / OpenSubtitles frequency lists

- **What**: subtitle-derived counts, strong for spoken/everyday frequency. Per-language
  lists (SUBTLEX-ES/IT/UK/US; OpenSubtitles for pt/fr).
- **Metadata**: raw counts, per-million, contextual diversity, sometimes POS.
- **Access**: per-list downloads (academic pages / OPUS). **Licenses vary per list** -
  check each.
- **Fit**: a second frequency opinion / spoken-register signal; optional in phase 6.

### WordNet `tag_count` (SemCor)

- **What**: per-**sense** tag counts (English), the only direct sense-frequency signal.
- **Access**: via `wn` `sense.counts()` (see [`metadata_catalog.md`](metadata_catalog.md)).
- **Fit**: weights for splitting token frequency across senses where no sense-tagged
  corpus exists (phase 6, English-anchored, `frequency_is_estimated=True` elsewhere).

## CEFR / difficulty sources (phase 6)

### Kelly project

- **What**: corpus-based, CEFR-graded frequency word lists. Covers **9 languages incl.
  English and Italian** (also Arabic, Chinese, Greek, Norwegian, Polish, Russian,
  Swedish). **pt/es/fr are not in Kelly** - a gap for three of our five.
- **Metadata**: lemma, POS, CEFR band, frequency rank.
- **Access**: [Kelly @ Språkbanken](https://spraakbanken.gu.se/en/projects/kelly) and
  [the Leeds mirror](https://ssharoff.github.io/kelly/). Swedish list is CC-BY-SA
  3.0 / LGPL 3.0; **per-language licensing varies - check each**.
- **Fit**: direct CEFR for en/it; pt/es/fr need another source or estimation.

### English Vocabulary Profile / Oxford 3000-5000

- **What**: CEFR-banded English vocabulary (A1-C2).
- **Metadata**: word, POS, CEFR level (EVP is sense-aware).
- **Access**: Oxford 3000/5000 by CEFR level as published PDFs
  ([Oxford 3000 by CEFR](https://www.oxfordlearnersdictionaries.com/external/pdf/wordlists/oxford-3000-5000/The_Oxford_3000_by_CEFR_level.pdf));
  EVP via the English Profile site (registration). **English only**, and **restrictively
  licensed** - usable as a reference/lookup, risky to redistribute. Treat as
  guidance, not a shippable table.
- **Fit**: English CEFR cross-check; not a multilingual answer.

### Per-language CEFR gap

There is **no single clean multilingual CEFR list** for en/pt/es/fr/it. Realistic plan
(phase 6): Kelly for en/it, official institute lists where they exist (e.g. Spanish
*Plan Curricular del Instituto Cervantes*, French *Référentiels*/CECRL lists, Italian
*Profilo della lingua italiana*), and an **estimated** band (frequency + length +
LLM judgment, `cefr_is_estimated=True`) wherever no graded list is available. Licensing
of each national list is its own phase-10 check.

## Example sentences (phase 6/8)

### Tatoeba

- **What**: crowd-sourced sentences with translations across many languages, all five
  covered.
- **Metadata**: sentence, language, links to translations, tags, audio for some.
- **Access**: CSV/SQLite dumps + API. **CC-BY 2.0 FR** (attribution, *not* share-alike) -
  friendlier than kaikki for an open dataset.
- **Fit**: a permissively-licensed `examples` source to complement/replace CC-BY-SA
  kaikki sentences. Joins by lemma membership; no sense alignment (same caveat as kaikki).

## Summary: licensing posture (feeds phase 10)

| Source | License | Ship verbatim in open dataset? |
| --- | --- | --- |
| OMW (per lexicon) | mixed, mostly permissive - **verify per lexicon** | yes, after per-lexicon check |
| CILI | open | yes |
| Wikidata Lexemes | **CC0** | yes (cleanest) |
| Tatoeba | CC-BY 2.0 FR | yes, with attribution |
| kaikki / Wiktionary | CC-BY-SA | only in isolated SA layer, or LLM-rewrite |
| ConceptNet | CC-BY-SA | same as kaikki |
| wordfreq (data) | mixed - **pin + verify** | derived numbers likely ok; check |
| Kelly | varies per language | per-language check |
| BabelNet / EVP / Oxford | restrictive | guidance/validation only, do not ship |

The **CC0 (Wikidata) + CC-BY (Tatoeba) + permissive-OMW** triangle is the cleanest open
core; CC-BY-SA sources (kaikki, ConceptNet) stay isolated or get LLM-rewritten.
