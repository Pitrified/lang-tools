# Prompt caching on the OpenAI API (phase 11 study, 2026-10-23)

These questions came up while scaling the look-alike verifier. Does caching exist on the
public API? Is it cheaper? Do we see it in the usage? Does putting the variable part last
cost quality? The answers below are measured on `gpt-6-luna` through the public API, the
same endpoint and key the project uses. The scripts are next to this file.

## Findings

- **It exists on the public API** (not a corporate-only feature), for Chat Completions and
  Responses alike.
- **The usage reports it.** Chat Completions puts it in `usage.prompt_tokens_details`
  (`cached_tokens`, `cache_write_tokens`). Responses puts it in
  `usage.input_tokens_details` (the same two fields, plus a TTL split of the writes).
- **Nothing is cached under 1024 prompt tokens.** The verifier's static instructions
  (prompt v5) are about 800 tokens, which is why every run so far shows
  `cached_tokens: 0`.
- **Implicit mode, the default, places the breakpoint at the end of the last message.**
  Every call therefore writes its own variable tail to the cache:
  - a write is billed at 1.25x input on GPT-5.6 and later;
  - a read is billed at 0.1x;
  - a one-message prompt whose variable part is most of the tokens gets more expensive
    with caching, not cheaper.

  Measured with a 1587-token prompt: the first call wrote 1584 tokens; the next calls read
  1563 and wrote the new 21-token tail.
- **Explicit mode fixes that.** Set `prompt_cache_options: {"mode": "explicit"}` (through
  `extra_body` on Chat Completions) and put
  `prompt_cache_breakpoint: {"mode": "explicit"}` on the static system content block. The
  first call writes only the static prefix (1554 tokens); later calls read it (1554
  cached) and write nothing. Explicit mode with no breakpoint turns caching off: no reads,
  no writes.
- **What it saves us.** Static prefix S, variable part V (about 2000 to 2400 tokens for 20
  pairs with senses), output O. A cached call bills about `0.1 S + V` input instead of
  `S + V`, plus one 1.25x write of S per 30 minutes.
  - With v5 (S about 800) there is nothing to gain: S is too short, and V dominates.
  - Caching makes a long static prefix nearly free. A prompt with about 40 worked
    examples (S about 2500) costs the same as a bare one. That is where caching pays.
- **Variable part last.** The caching layout puts the instructions first and the items
  last, and v5 already does so. A quality A/B (v5 versus the same text with the pairs
  first) is wired in `verify_experiments.py` (variant `v5-varfirst`). It was not run: we
  parked the paid path for the harness review.
- **The Batch API is an open question.** Community threads disagree on whether cache
  discounts apply to batch jobs. Probe batch `batch_6adb331091b08190aaa39f6180c67e3e`
  (id in `batch_probe_id.txt`) holds six requests sharing a 1550-token prefix: three
  implicit, three explicit. Read it with `uv run python cache_probe_batch.py check` and
  record the per-request `cached_tokens` here. It was still `in_progress` on 2026-10-23.
- **Our usage tracking misses writes.** `llm.runner.Usage` reads `cached_tokens` but not
  `cache_write_tokens`, and `UsageTotals.cost` bills no write surcharge. Add both before
  any cached paid run.

## Files

- `cache_probe_batch.py`: submits and checks the batch probe.
- `verify_experiments.py`: the parked verifier harness over the 1000-pair gold set. It
  covers prompt variants, the variable-first layout, a cached v6 with worked examples and
  meanings-first output, trap and cognate scores per gold origin, and cache-aware cost.
- `verify_v6_static.txt`: the v6 static prompt. Its worked examples are pairs outside
  the gold set.
