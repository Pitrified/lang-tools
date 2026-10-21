"""Non-English gloss backfill as one OpenAI batch: plan | submit --yes | status | collect.

Model `gpt-6-luna`, prompt `gloss_translate/v3`, reasoning off - chosen in
`gloss_model_comparison.md`. Built to survive a closed session or a reclaimed
container:

- The batch runs on OpenAI's side; nothing local needs to stay alive.
- `submit` writes a small manifest, `gloss_backfill_batch.json`, next to this script
  (batch id, input file, model, prompt hash, counts, git commit). Commit it right
  away: it is the durable pointer to the batch.
- The batch is tagged with metadata (`JOB_TAG`), so `status` / `collect` can find it
  again by listing the account's batches even if the manifest were lost.
- Re-running `submit` never pays twice: while the batch is alive or completed, the
  runner returns its id instead of uploading a new one.
- `collect` rebuilds everything it needs from the corpus (deterministic from the
  committed code + pinned sources), so it works from any fresh checkout with an
  OpenAI key. It writes the results into the committed curated file
  ``data/curated/gloss_backfill.jsonl`` (every row ``proposed`` or ``rejected``)
  and a 50-per-language review sample, `gloss_backfill_review_sample.md`.

Deadlines (OpenAI Batch docs): the batch must finish within 24 h (unfinished
requests are then cancelled and the completed ones returned); the output file is
**deleted 30 days after completion**, so `collect` must run within that window.

Run from the repo root with the project venv:

    uv run python scratch_space/09_concept_model/08_maintenance/gloss_backfill_job.py plan
"""

import collections
from datetime import UTC
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys

os.environ.setdefault("SAMPLE_API_KEY", "placeholder-not-a-secret")
os.environ.setdefault("OPENAI_API_KEY", "proxy-injected")

from llm_core.chat.config.openai import ChatOpenAIConfig

from lang_tools.lexicon.ingestion.gloss_backfill import check_glosses
from lang_tools.lexicon.ingestion.gloss_backfill import chunk_items
from lang_tools.lexicon.ingestion.gloss_backfill import missing_glosses
from lang_tools.lexicon.ingestion.gloss_backfill import review_sample
from lang_tools.lexicon.maintenance import GLOSS_BACKFILL_FILE
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import write_jsonl
from lang_tools.llm.gloss_translate import build_gloss_translate_chain
from lang_tools.llm.runner import collect_batch
from lang_tools.llm.runner import find_batches
from lang_tools.llm.runner import load_checkpoint
from lang_tools.llm.runner import prompt_sha
from lang_tools.llm.runner import read_records
from lang_tools.llm.runner import submit_batch
from lang_tools.llm.runner import summarize_usage
from lang_tools.params.lang_tools_params import get_lang_tools_params

MODEL = "gpt-6-luna"
PROMPT_VERSION = "3"
EXTRA_BODY = {"reasoning_effort": "none"}
JOB_TAG = {"job": "lang-tools-gloss-backfill", "prompt": f"gloss_translate/v{PROMPT_VERSION}"}
#: Batch prices per 1M tokens (developers.openai.com/api/docs/pricing, 2026-10-21).
PRICES = {"input_per_m": 0.05, "cached_per_m": 0.005, "output_per_m": 0.25}
#: Measured on the 100-gloss comparison (gpt-6-luna + v3): tokens per gloss.
MEASURED_PER_GLOSS = {"input": 5393 / 100, "output": 3087 / 100}

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "gloss_backfill_batch.json"
REVIEW = HERE / "gloss_backfill_review_sample.md"

data_fol = get_lang_tools_params().paths.data_fol
work = data_fol / "_raw" / "lexicon" / "maintenance" / "gloss_backfill_batch"
checkpoint = work / "run.jsonl"
chain = build_gloss_translate_chain(ChatOpenAIConfig(model=MODEL), version=PROMPT_VERSION)


def _git_commit() -> str:
    out = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
        cwd=HERE,
    )
    return out.stdout.strip() or "unknown"


def _batch_id() -> str:
    """Return the batch id: the committed manifest first, else found by tag."""
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))["batch_id"]
    found = find_batches(JOB_TAG)
    if not found:
        sys.exit("No manifest and no batch tagged with this job on the account.")
    print(f"manifest missing; found {len(found)} tagged batch(es), using the newest")
    return found[0].id


items = missing_glosses(data_fol)
chunks = chunk_items(items)
per_lang = collections.Counter(item.language for item in items)
step = sys.argv[1] if len(sys.argv) > 1 else "plan"

if step == "plan":
    tokens_in = MEASURED_PER_GLOSS["input"] * len(items)
    tokens_out = MEASURED_PER_GLOSS["output"] * len(items)
    cost = (tokens_in * PRICES["input_per_m"] + tokens_out * PRICES["output_per_m"]) / 1e6
    print(f"model {MODEL}, prompt v{PROMPT_VERSION} ({prompt_sha(chain)}), reasoning none")
    print(f"glosses {len(items)} {dict(per_lang)}; requests {len(chunks)} (one batch)")
    print(f"estimated from the measured sample: {tokens_in / 1e6:.1f}M in, "
          f"{tokens_out / 1e6:.1f}M out, ~${cost:.2f} at batch prices")
    print("nothing submitted. To run: ... gloss_backfill_job.py submit --yes")

elif step == "submit":
    if "--yes" not in sys.argv:
        sys.exit("Refusing to submit without --yes (this is a paid run).")
    batch_id = submit_batch(
        chain,
        chunks,
        checkpoint=checkpoint,
        workdir=work,
        extra_body=EXTRA_BODY,
        metadata={**JOB_TAG, "git": _git_commit()},
    )
    manifest = {
        "batch_id": batch_id,
        "model": MODEL,
        "prompt": f"gloss_translate/v{PROMPT_VERSION}",
        "prompt_sha": prompt_sha(chain),
        "reasoning_effort": EXTRA_BODY["reasoning_effort"],
        "requests": len(chunks),
        "glosses": len(items),
        "glosses_per_language": dict(sorted(per_lang.items())),
        "git_commit": _git_commit(),
        "submitted_at": datetime.now(tz=UTC).isoformat(timespec="seconds"),
        "metadata": JOB_TAG,
        "note": "Collect within 30 days of completion (OpenAI deletes the output file).",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(f"submitted {batch_id}; wrote {MANIFEST} - commit it now")

elif step == "status":
    from openai import OpenAI

    batch = OpenAI().batches.retrieve(_batch_id())
    print(batch.id, batch.status, batch.request_counts)

elif step == "collect":
    status = collect_batch(chain, _batch_id(), checkpoint=checkpoint)
    if status != "completed":
        sys.exit(f"batch is {status}; nothing collected yet")
    outputs = load_checkpoint(checkpoint, chain.output_model)
    by_key = {item.key: item for item in items}
    proposals, unmatched = [], 0
    for output in outputs.values():
        found = [by_key[g.key] for g in output.glosses if g.key in by_key]
        # A gloss whose key the model mistyped matches no item: dropped, left missing.
        unmatched += len(output.glosses) - len(found)
        proposals += check_glosses(found, output)
    write_jsonl(proposals, curated_path(data_fol, GLOSS_BACKFILL_FILE))
    totals = summarize_usage(read_records(checkpoint))
    print(f"chunks {len(outputs)}/{len(chunks)}, glosses {len(proposals)} "
          f"({unmatched} returned under a mistyped key; "
          f"{len(items) - len(proposals)} still missing), "
          f"{collections.Counter(p.status for p in proposals)}")
    print(f"usage: {totals.input_tokens} in, {totals.output_tokens} out, "
          f"{totals.reasoning_tokens} reasoning; cost ${totals.cost(**PRICES):.2f}")
    lines = [
        "# Gloss backfill - review sample (50 per language)",
        "",
        "Read these, then accept the run (or the languages that pass) with "
        "`gloss_backfill.accept_run` on `data/curated/gloss_backfill.jsonl`.",
        "",
    ]
    for p in review_sample(proposals, per_language=50):
        item = by_key[f"{p.language}:{p.concept_id.rsplit('__', 1)[1]}"]
        lines.append(f"- [{p.language}] **{item.english_definition}** -> {p.proposed_definition}")
    REVIEW.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {curated_path(data_fol, GLOSS_BACKFILL_FILE)} and {REVIEW} - commit both")

else:
    sys.exit(f"unknown step {step!r}: plan | submit --yes | status | collect")
