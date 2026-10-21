"""Gloss model comparison: 4 chunks (one per language) x 4 models via batch.

Steps: submit | collect | report. Writes everything under the gitignored
data/_raw/lexicon/maintenance/gloss_compare/<model>/.
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
from lang_tools.llm.runner import collect_batch
from lang_tools.llm.runner import load_checkpoint
from lang_tools.llm.runner import read_records
from lang_tools.llm.runner import submit_batch
from lang_tools.llm.runner import summarize_usage
from lang_tools.params.lang_tools_params import get_lang_tools_params

#: model -> (reasoning effort, batch $/1M input, cached input, output); prices from
#: developers.openai.com/api/docs/pricing, read 2026-10-21.
MODELS = {
    "gpt-6-luna": ("none", 0.05, 0.005, 0.25),
    "gpt-5.6-luna": ("none", 0.10, 0.01, 0.60),
    "gpt-5-nano": ("minimal", 0.025, 0.0025, 0.20),
    "gpt-5-mini": ("minimal", 0.125, 0.0125, 1.00),
}

data_fol = get_lang_tools_params().paths.data_fol
root = data_fol / "_raw" / "lexicon" / "maintenance" / "gloss_compare"
items = missing_glosses(data_fol)
chunks = chunk_items(items)
by_lang = collections.defaultdict(list)
for key, chunk in chunks:
    by_lang[key.split(":")[0]].append((key, chunk))
picked = [lang_chunks[len(lang_chunks) // 2] for _, lang_chunks in sorted(by_lang.items())]
print("chunks", [k for k, _ in picked], "glosses", sum(len(c.concepts) for _, c in picked))
step = sys.argv[1]
by_key = {item.key: item for item in items}

for model, (effort, p_in, p_cached, p_out) in MODELS.items():
    chain = build_gloss_translate_chain(ChatOpenAIConfig(model=model))
    work = root / model
    cp = work / "run.jsonl"
    if step == "submit":
        bid = submit_batch(
            chain, picked, checkpoint=cp, workdir=work,
            extra_body={"reasoning_effort": effort},
        )
        print(model, effort, bid)
    elif step == "collect":
        print(model, collect_batch(chain, (work / "batch_id.txt").read_text(), checkpoint=cp))
    elif step == "report":
        records = read_records(cp)
        totals = summarize_usage(records)
        cost = totals.cost(input_per_m=p_in, output_per_m=p_out, cached_per_m=p_cached)
        outputs = load_checkpoint(cp, chain.output_model)
        rows = []
        for key, chunk in picked:
            if key in outputs:
                rows += check_glosses([by_key[c.key] for c in chunk.concepts], outputs[key])
        reasons = collections.Counter(r.rationale or "ok" for r in rows)
        n = max(1, len(rows))
        print(
            f"{model:14} {effort:8} chunks_ok={len(outputs)}/4 glosses={len(rows)} "
            f"in={totals.input_tokens} out={totals.output_tokens} "
            f"reasoning={totals.reasoning_tokens} cost=${cost:.4f} "
            f"per_1k_glosses=${cost / n * 1000:.3f} full_backfill~${cost / n * len(items):.2f} "
            f"{dict(reasons)}",
        )
        (work / "glosses.json").write_text(
            json.dumps({r.language + ":" + r.concept_id.rsplit("__", 1)[1]: r.proposed_definition for r in rows}, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
