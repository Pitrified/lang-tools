# Lemma identity and per-sense frequency (decided 2026-10-21, not yet implemented)

Two defects found during the phase-8 member-form review. The user decided both are wrong
("avó and avô are not the same thing"; "beryllium is not *be*"). This note records the
measurements, the shape of the fix and its cost. **Nothing here is implemented yet.**

## 4a - lemma identity must not fold accents

`lemma_id(text, language)` hashes `f"{language}::{normalize(text)}"`, and `normalize` lowercases
**and** strips diacritics. So any two forms that differ only by accent are one lemma, with one
id, one display text (`_LemmaTally` picks the majority variant) and the union of their senses.

Measured on OMW 1.4 (variant groups that would split under an accent-sensitive id; "disjoint"
means the variants never share a synset, i.e. they are different words):

| lang | forms with accents | accent-merged groups | of which disjoint (different words) | examples |
| --- | --- | --- | --- | --- |
| pt | 16,418 | 1,976 | 139 | `avó`/`avô`, `alias`/`aliás`, `avaro`/`ávaro` |
| fr | 14,092 | 397 | 142 | `mais`/`maïs`, `même`/`mémé`/`mème`, `bailler`/`bâiller` |
| es | 8,098 | 117 | 51 | **`ordenar`/`ordeñar`**, `dinar`/`diñar` (`ñ` is a letter, and `normalize` strips its tilde) |
| it | 1,450 | 32 | 14 | `papa`/`papà`, `meta`/`metà`, `casino`/`casinò` |

The remaining accent-merged groups share synsets: one word spelled two ways (`cómodo` /
`cômodo` across pt norms, `heroico` / `heróico` before and after a spelling reform). An
accent-sensitive id splits those too; they become two lemmas on the same concept, which is
correct for a spelling learner but doubles some entries.

## 4b - beryllium is not *be*

Two separate causes.

1. **Identity folds case.** `Be` (beryllium), `be` (verb) are one lemma for the same reason as
   4a. Case-merged groups, measured the same way:

   | lang | case-merged groups | of which disjoint (different words) | examples |
   | --- | --- | --- | --- |
   | en | 1,406 | 1,371 | `State`/`state`, `Advent`/`advent`, `Be`/`be`, `SHAPE`/`shape` |
   | fr | 3,989 | 501 | `OU`/`ou`, `Père`/`père`, `OK`/`ok` |
   | pt | 6,761 | 576 | `Cuspir`/`cuspir`, `Abstrato`/`abstrato` (mostly capitalization noise) |
   | es | 309 | 187 | `Diana`/`diana`, `Remo`/`remo`, `Muerte`/`muerte` |
   | it | 126 | 70 | `Argentina`/`argentina`, `Babilonia`/`babilonia` |

   In English almost every case pair is two words; in pt / fr most are one word with stray
   capitals. So "case-sensitive" is not a rule by itself: case variants that **share a synset**
   are orthographic noise and should collapse to the lowercase form, while variants on
   disjoint synsets are different words and should stay apart.
2. **The CEFR overlay reads the token's frequency for every sense.** Even as its own lemma,
   `Be` would still score A1: `wordfreq` lowercases its input, so `Be` gets `be`'s frequency.
   The fix is on the frequency side, not identity: a lemma whose form differs from a
   more frequent lowercase lemma must not inherit that lemma's token frequency (fall back to
   the sense frequency, or mark the token frequency unknown / estimated).

## Shape of the fix

- **Identity key**: `lemma_id` hashes the form with case and accents kept (NFC-normalized,
  whitespace-trimmed). Lowercase unaccented forms keep their current id, because their key
  string does not change; only forms with a capital or a diacritic get a new id.
- **Build rule for case noise**: in `group_to_records`, a capitalized form whose lowercase
  variant is a member of the same synset is folded to the lowercase lemma (deterministic,
  measurable: ~6,200 pt groups, ~3,500 fr). Disjoint case variants stay separate.
- **`Lemma.normalized`** keeps folding case and accents. It is the search / diacritic-typing
  key, not the identity, so accent-insensitive lookup still works.
- **Frequency**: `sources.frequency.lemma_zipf` stops lending a lowercase token's frequency to
  a case-distinct lemma; the CEFR overlay then follows. This moves bands, so phase 6's Kelly
  validation re-runs and `CEFR_CUTOFFS` is re-fitted, joining the re-fit question already open
  from phase 7.

## Complexity

| piece | code | data / downstream |
| --- | --- | --- |
| identity key (4a + 4b.1) | small: `lemma_id` + its tests | lemma and sense ids change for every lemma with a capital or a diacritic (tens of thousands); rebuild; seed regenerated; `sense_relations` follow automatically |
| case-noise collapse rule | medium: rule + tests + a measurement to confirm it does not merge real pairs | new review surface (sampled, like the other phase-8 rules) |
| curated inputs | small | `member_form_drops.jsonl` is keyed on `lemma_id` and must be re-keyed from its stored `form`; gloss overrides, slug qualifiers and topics are concept-keyed and unaffected |
| frequency + CEFR (4b.2) | medium | bands move; Kelly re-validation and a cutoff re-fit (phase 6 territory) |
| `lang-tutor` | none here | its per-user progress is keyed on lemma ids, so affected ids reset; it is being reworked in phase 9 anyway, which is the natural time to land this |

Overall: a few days of careful work, mostly measurement and review rather than code, with one
id migration. It should land as its own step - after the phase-8 worklists settle and before
phase 9 reconnects `lang-tutor` - so the id churn happens once.
