"""gpt-6-luna on the same 4 comparison chunks, live (not batch), reasoning off.

Usage: compare_gloss_models_live.py [prompt_version]  (default "2"; "3" = no added facts)
"""

import collections
import json
import os
import sys

os.environ.setdefault("SAMPLE_API_KEY", "placeholder-not-a-secret")
os.environ.setdefault("OPENAI_API_KEY", "proxy-injected")

from llm_core.chat.config.openai import ChatOpenAIConfig

from lang_tools.lexicon.ingestion.gloss_backfill import check_glosses
from lang_tools.lexicon.ingestion.gloss_backfill import chunk_items
from lang_tools.lexicon.ingestion.gloss_backfill import missing_glosses
from lang_tools.llm.gloss_translate import build_gloss_translate_chain
from lang_tools.llm.runner import read_records
from lang_tools.llm.runner import run_chain
from lang_tools.llm.runner import summarize_usage
from lang_tools.params.lang_tools_params import get_lang_tools_params


class NoReasoningConfig(ChatOpenAIConfig):
    """ChatOpenAIConfig with reasoning turned off (llm-core has no passthrough)."""

    reasoning_effort: str = "none"


MODEL = "gpt-6-luna"
PRICES = {"input_per_m": 0.10, "cached_per_m": 0.01, "output_per_m": 0.50}  # standard tier

data_fol = get_lang_tools_params().paths.data_fol
root = data_fol / "_raw" / "lexicon" / "maintenance" / "gloss_compare"
VERSION = sys.argv[1] if len(sys.argv) > 1 else "2"
TAG = MODEL if VERSION == "2" else f"{MODEL}-v{VERSION}"
work = root / (f"{MODEL}-live" if VERSION == "2" else f"{TAG}-live")
items = missing_glosses(data_fol)
by_key = {item.key: item for item in items}
by_lang = collections.defaultdict(list)
for key, chunk in chunk_items(items):
    by_lang[key.split(":")[0]].append((key, chunk))
picked = [lang_chunks[len(lang_chunks) // 2] for _, lang_chunks in sorted(by_lang.items())]
print("chunks", [k for k, _ in picked])

chain = build_gloss_translate_chain(NoReasoningConfig(model=MODEL), version=VERSION)
outputs = run_chain(chain, picked, checkpoint=work / "run.jsonl", concurrency=4)
records = read_records(work / "run.jsonl")
for r in records:
    print(r.key, "error:" if r.error else "ok", (r.error or "")[:200], r.usage)
totals = summarize_usage(records)
rows = []
for key, chunk in picked:
    if key in outputs:
        rows += check_glosses([by_key[c.key] for c in chunk.concepts], outputs[key])
cost = totals.cost(**PRICES)
n = max(1, len(rows))
print(
    f"{TAG} none chunks_ok={len(outputs)}/4 glosses={len(rows)} in={totals.input_tokens} "
    f"out={totals.output_tokens} reasoning={totals.reasoning_tokens} cost=${cost:.4f} "
    f"full_backfill~${cost / n * len(items):.2f} (standard) "
    f"~${cost / n * len(items) / 2:.2f} (batch) {dict(collections.Counter(r.rationale or 'ok' for r in rows))}",
)
(root / TAG).mkdir(parents=True, exist_ok=True)
(root / TAG / "glosses.json").write_text(
    json.dumps(
        {r.language + ":" + r.concept_id.rsplit("__", 1)[1]: r.proposed_definition for r in rows},
        ensure_ascii=False,
        indent=1,
    ),
    encoding="utf-8",
)
