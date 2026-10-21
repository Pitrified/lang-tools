# Gloss backfill - quality assessment (2026-10-21)

Review of the `gpt-6-luna` + `gloss_translate/v3` backfill in
`data/curated/gloss_backfill.jsonl` (174,315 `proposed` rows after the hand fixes). Read: the
200-row sample in [`gloss_backfill_review_sample.md`](gloss_backfill_review_sample.md), plus
corpus-wide counts over every proposed row and 10 random rows from each flagged category.

## Verdict

**Accept all four languages.** Meaning is right in every sampled row; no invented facts, no
headword prefixes, no English left behind. The defects are typographic and consistent, so they
are best fixed mechanically rather than by review or another paid run.

## Content

- Faithful and idiomatic in all four languages: es "Libro de bolsillo en edición rústica",
  fr "Cuire à chaleur sèche, généralement au four", it "Capriola all'indietro", pt "Matriz
  obtida pela troca das linhas pelas colunas de uma matriz dada". Varieties hold (pt-BR
  "acúmulo", "lipídios", "canadense"; neutral es).
- Bare taxon glosses ("storks", "scallops") get a rank-qualified gloss ("Famille d'oiseaux
  comprenant les cigognes", "Moluscos bivalves da família Pectinidae"). The rank comes from the
  member names and checked out on the flagged rows (no genus/family mismatch beyond 3 pt rows
  that are correct "type genus of ..." glosses).
- Weak spots, rare and harmless: a few calques of English common names (fr "Groseilles de mer"
  for ctenophores, pt "salamandras olímpicas"); a few awkward rank phrasings ("conhecida como
  Timaliidae"); ~130 glosses (0.08%) shorter than 0.4x the English that drop a trailing clause
  (es "Ingeniero y fabricante alemán de automóviles" without what he built), mostly where the
  English carries a usage note in backquotes.
- ~725 rows (0.4%) longer than 2.5x the English are almost all short verb or taxon glosses
  made explicit ("combine into one" -> "unir varios elementos para formar uno solo"), not
  padding.

## Typography - inconsistent, mechanical to fix

| | es | fr | it | pt |
| --- | --- | --- | --- | --- |
| proposed rows | 38,512 | 59,077 | 32,832 | 43,894 |
| starts lowercase | 10% | 8% | 11% | 21% |
| no final period | 10% | 8% | 11% | 20% |
| curly apostrophe `’` | 0% | 44% | 18% | 0% |
| en/em dash | 13 | 43 | 5 | 1,674 |

The model mixes two styles: mostly "Capitalized sentence.", sometimes "lowercase fragment".
The corpus convention is the second: 93% of English OMW glosses and 99% of the OMW Italian
ones start lowercase and have no final period. pt also writes year ranges with an en dash
(`1801–1835`) where the English has `1801-1835`; fr and it mix `’` and `'`.

Proposed normalization (free, deterministic, applied in `apply_gloss_backfill` at build time
so the committed proposals stay as generated): lowercase the first letter unless the English
gloss starts with a capital (proper nouns: "Isola ...", "Hegel ..."), strip one final period,
en/em dash between digits -> `-`, `’` -> `'`. Not yet implemented.
