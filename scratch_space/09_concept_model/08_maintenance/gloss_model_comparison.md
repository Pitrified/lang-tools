# Phase 8 - gloss backfill model comparison (2026-10-21)

Which OpenAI model should write the 174,319 missing non-English glosses (fr 59,079, pt
43,895, es 38,512, it 32,833)? Decided from a measured sample, not from price lists: the
first three phase-8 LLM jobs ran on `gpt-5-mini` without a comparison or measured usage, and
the cost estimate in [`../08_maintenance.md`](../08_maintenance.md) turned out low because
hidden reasoning was most of the output. This note records the measurement that replaced the
guess.

Side-by-side outputs for all 100 glosses: [`gloss_model_comparison_samples.md`](gloss_model_comparison_samples.md).
Scripts that produced them: [`compare_gloss_models_batch.py`](compare_gloss_models_batch.py),
[`compare_gloss_models_live.py`](compare_gloss_models_live.py).

## What reasoning cost on the earlier jobs

Measured from the slug tier-2 batch output (9,742 requests, `gpt-5-mini`, reasoning effort
`low`): 4.41M input tokens, 3.13M output tokens, of which **2.33M (74%) were hidden
reasoning**. Per request: 452 in, 322 out, 239 of them reasoning. At batch prices that is
about $3.70, of which ~$2.33 was reasoning a gloss-word qualifier does not need. The form
review (970 live calls, default reasoning) ran before usage was tracked; its cost is
estimated at $1-2. Total phase-8 spend so far: roughly $5-7.

Usage is now recorded on every runner record (`llm.runner.Usage`, `summarize_usage`,
`UsageTotals.cost`), so every future estimate is measured on a sample first.

## Setup

- The same 4 chunks for every model, one per language (the middle chunk of each language's
  key-sorted worklist), 25 concepts each: 100 glosses. Prompt `gloss_translate/v2`
  (Brazilian Portuguese, neutral Spanish).
- Reasoning off: `none` for the 5.6 / 6 models; `minimal` (the lowest accepted) for
  `gpt-5-nano` / `gpt-5-mini`. Measured reasoning tokens were 0 for all four.
- Candidates chosen with the user: the GPT-4 family and `gpt-5.4-mini` excluded (old /
  too expensive); `gpt-6.1-luna` does not exist (the only 6.1 model is `gpt-6.1-sol`, ~20x
  the price).
- `gpt-5.6-luna`, `gpt-5-nano`, `gpt-5-mini` ran as one small Batch each. `gpt-6-luna`'s batch
  sat at 0/4 for ~1.5 h while the others finished, so it was cancelled (nothing billed) and
  the same chunks were run live instead (20 s).
- Prices: [OpenAI API pricing](https://developers.openai.com/api/docs/pricing), read
  2026-10-21 (per 1M tokens, batch tier: `gpt-6-luna` 0.05 / 0.25, `gpt-5.6-luna` 0.10 /
  0.60, `gpt-5-nano` 0.025 / 0.20, `gpt-5-mini` 0.125 / 1.00; standard tier is double).

## Results

| model | reasoning | in / out tokens | cost of the 100 | full backfill, batch | full backfill, live | failed the screen |
| --- | --- | --- | --- | --- | --- | --- |
| `gpt-6-luna` | none | 4,833 / 3,182 | $0.0021 (standard) | ~$1.80 | ~$3.60 | 1 (runaway length) |
| `gpt-5.6-luna` | none | 4,833 / 3,152 | $0.0024 (batch) | ~$4.10 | ~$8.30 | 0 |
| `gpt-5-nano` | minimal | 4,833 / 3,671 | $0.0009 (batch) | ~$1.50 | ~$3.00 | 9 (runaway length) |
| `gpt-5-mini` | minimal | 4,833 / 4,227 | $0.0048 (batch) | ~$8.40 | ~$16.80 | 4 (3 runaway, 1 missing) |

"Full backfill" scales the measured cost per gloss to all 174,319 glosses.

## Quality

Read side by side on the 100 (see the samples file):

- **`gpt-5.6-luna` - most faithful.** Renders the English gloss and adds nothing: es "Delantero
  de un equipo de fútbol.", fr "Élément transuranien.", it "Persona che educa i giovani."
- **`gpt-6-luna` - nearly identical**, with occasional true-but-unrequested additions: "a
  transuranic element" -> "Élément chimique transuranien de numéro atomique 107"; "a forward on
  a soccer team" -> "...cuya función principal es marcar goles" (its one screen failure).
- **`gpt-5-nano` - cheapest, least reliable.** Prefixes invented headwords ("Forer: coup
  léger...", "wampum: ...") and invents facts ("Unnilhexium (bh) ... nom historique utilisé pour
  Bohrium").
- **`gpt-5-mini` - fluent, embellishes.** "a gentle blow" -> "coup léger et bref donné avec la
  main ou un objet"; a garbled "(mien: bohrium)". Twice `gpt-5.6-luna`'s price.

## Second pass: `gpt-6-luna` with prompt v3

`gpt-6-luna`'s one weakness was true-but-unrequested detail. Prompt `gloss_translate/v3`
keeps the request for a natural, idiomatic rendering (explicitly not word for word) and adds a
negative list: no facts the English gloss does not state (atomic numbers, dates, places,
taxonomy), no purpose or usage unless stated, no examples or synonyms, no leading headword; a
short gloss stays short. Same 4 chunks, live, reasoning `none`.

| | in / out tokens | cost of the 100 | full backfill, batch / live | failed the screen | median length vs English |
| --- | --- | --- | --- | --- | --- |
| `gpt-6-luna` + v3 | 5,393 / 3,087 | $0.0021 (standard) | ~$1.80 / ~$3.60 | 0 | 1.12x |
| `gpt-6-luna` + v2 | 4,833 / 3,182 | $0.0021 (standard) | ~$1.80 / ~$3.60 | 1 | 1.18x |
| `gpt-5.6-luna` + v2 | 4,833 / 3,152 | $0.0024 (batch) | ~$4.10 / ~$8.30 | 0 | 1.16x |

v3 changed 49 of the 100 glosses, and the additions are gone: fr "Élément chimique
transuranien de numéro atomique 107" -> "Élément chimique transuranien"; "Serpent venimeux du
genre Bothrops" -> "Serpent du genre Bothrops"; es "... cuya función principal es marcar goles"
-> "Jugador de la línea ofensiva de un equipo de fútbol"; "plain wanderer" no longer names its
genus. It still reads as native prose rather than a calque (es "Que resulta ofensivo para la
mente"; "Elemento químico situado más allá del uranio en la tabla periódica"). Worth noting:
`gpt-5.6-luna` had added the atomic number too (es "de número atómico 107"), so the habit was
not unique to `gpt-6-luna`.

## Recommendation

After the second pass, **`gpt-6-luna` with prompt v3**: on this sample it is as faithful as
`gpt-5.6-luna`, the most concise of the three, and half the price per token (~$1.80 by batch,
~$3.60 live). The open risk is operational, not quality: its batch queue did not start in
1.5 h, so the full run may have to go live, which takes hours at modest concurrency (not yet
measured against the rate limits). `gpt-5.6-luna` with v3 was not tested. Not yet decided -
see the next steps in [`../08_maintenance.md`](../08_maintenance.md).
