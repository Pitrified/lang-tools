"""Verifier experiments on the 1000-pair gold set: prompt variant x layout x caching.

Parked (2026-10-23) in favour of reviewing the candidates through the agent
harness (see ``11_false_friends.md``), kept so the cheap-model path can be
picked up again.

Variants:
    v5: the current prompt, one system message (pairs last).
    v5-varfirst: the same text with the pairs block moved first, to test
        whether the position of the variable part changes quality.
    v6: ``verify_v6_static.txt`` as a cached system message (explicit
        breakpoint), the language names and the items in the user message;
        the model writes both meanings before the kind.
    v6-noex: v6 without the worked examples.
    v6-nocache: v6 with caching disabled (explicit mode, no breakpoint).

Usage:
    uv run python verify_experiments.py VARIANT [MODEL] [EFFORT]

Each run checkpoints one line per chunk under ``RUNS`` (resumable) and prints
trap recall, false alarms, cognate precision, usage and live cost.
"""

from collections import Counter
import concurrent.futures as cf
import json
import os
from pathlib import Path
import sys
import threading
import time
from typing import Literal

from jinja2 import Template
from openai import OpenAI
from pydantic import BaseModel

from lang_tools.lexicon import get_store
from lang_tools.lexicon.ingestion.lookalikes import GoldPair
from lang_tools.lexicon.ingestion.lookalikes import LookalikeCandidate
from lang_tools.lexicon.ingestion.lookalikes import is_trap
from lang_tools.lexicon.ingestion.lookalikes import load_gold
from lang_tools.lexicon.ingestion.lookalikes import verify_chunks
from lang_tools.llm.lookalike_verify import LookalikeVerifyInput
from lang_tools.params.lang_tools_params import get_lang_tools_params

HERE = Path(__file__).parent
REPO = HERE.parents[2]
RUNS = get_lang_tools_params().paths.cache_fol / "lookalike_verify_runs"
V5 = (REPO / "src/lang_tools/prompts/lookalike_verify/v5.jinja").read_text()
V6_STATIC = (HERE / "verify_v6_static.txt").read_text()
#: Live $/1M tokens (input, cached input, output); batch is half. Cache writes bill 1.25x input.
PRICES = {
    "gpt-6-luna": (0.10, 0.01, 0.50),
    "gpt-5.6-luna": (0.20, 0.02, 1.20),
    "gpt-6.1-sol": (2.00, 0.10, 10.00),
}
TRAPS = {"full", "partial"}
RETRIES = 3

Kind = Literal["full", "partial", "cognate", "unrelated"]


class V5Verdict(BaseModel):
    """A v5 verdict."""

    key: str
    kind: Kind
    same_root: bool
    note: str


class V5Out(BaseModel):
    """The v5 output."""

    verdicts: list[V5Verdict]


class V6Verdict(BaseModel):
    """A v6 verdict: the two meanings come first, as a light reasoning step."""

    key: str
    target_meaning: str
    known_meaning: str
    same_root: bool
    kind: Kind
    note: str


class V6Out(BaseModel):
    """The v6 output."""

    verdicts: list[V6Verdict]


def _items(inp: LookalikeVerifyInput) -> str:
    return "\n".join(
        f"- {p.key}: {p.target_word} [{p.target_senses}] | {p.known_word} [{p.known_senses}]"
        for p in inp.pairs
    )


def build_messages(
    variant: str, inp: LookalikeVerifyInput
) -> tuple[list[dict], type[BaseModel], dict]:
    """Return ``(messages, output model, extra_body)`` for one chunk."""
    if variant.startswith("v5"):
        text = Template(V5).render(**inp.model_dump())
        if variant == "v5-varfirst":
            head, rest = text.split("Pairs (key", 1)
            pairs, ret = rest.split("Return `verdicts`", 1)
            text = "Pairs (key" + pairs + "\n" + head + "\nReturn `verdicts`" + ret
        return [{"role": "system", "content": text}], V5Out, {}
    user = (
        f"Target language: {inp.target_language_name}. Known language: {inp.known_language_name}.\n"
        f"Items (key: target word [its senses] | known word [its senses]):\n{_items(inp)}"
    )
    static = V6_STATIC
    if variant == "v6-noex":
        static = (
            static[: static.index("Worked examples")]
            + static[static.index("Return `verdicts`") :]
        )
    explicit = {"prompt_cache_options": {"mode": "explicit"}}
    if variant == "v6-nocache":
        return (
            [{"role": "system", "content": static}, {"role": "user", "content": user}],
            V6Out,
            explicit,
        )
    block = {
        "type": "text",
        "text": static,
        "prompt_cache_breakpoint": {"mode": "explicit"},
    }
    return (
        [{"role": "system", "content": [block]}, {"role": "user", "content": user}],
        V6Out,
        explicit,
    )


def main() -> None:  # noqa: C901 - a linear experiment script
    """Run one variant over the gold set and print its scores."""
    variant = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else "gpt-6-luna"  # noqa: PLR2004
    effort = sys.argv[3] if len(sys.argv) > 3 else "none"  # noqa: PLR2004
    size = int(os.environ.get("CHUNK", "20"))
    gold = load_gold(get_lang_tools_params().paths.data_fol)
    cands = [
        LookalikeCandidate(
            target_id=g.pt_lemma_id,
            target_text=g.pt,
            known_id=g.other_lemma_id,
            known_text=g.other,
            known_language=g.other_language,
            similarity=0.0,
            kind="full",
            shares_concept=False,
        )
        for g in gold
    ]
    chunks = verify_chunks(get_store(), cands, size=size)
    RUNS.mkdir(parents=True, exist_ok=True)
    out_path = RUNS / f"{variant}__{model}__{effort}__c{size}.jsonl"
    done: dict[str, dict] = {}
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            rec = json.loads(line)
            if rec.get("verdicts") is not None:
                done[rec["chunk"]] = rec
    client = OpenAI()
    lock = threading.Lock()

    def call(chunk_key: str, inp: LookalikeVerifyInput) -> dict:
        msgs, out_model, extra = build_messages(variant, inp)
        rec: dict = {}
        for attempt in range(RETRIES):
            try:
                t0 = time.time()
                resp = client.chat.completions.parse(
                    model=model,
                    messages=msgs,  # type: ignore[arg-type]
                    response_format=out_model,
                    reasoning_effort=effort,  # type: ignore[arg-type]
                    extra_body=extra or None,
                )
                parsed = resp.choices[0].message.parsed
                rec = {
                    "chunk": chunk_key,
                    "verdicts": [v.model_dump() for v in parsed.verdicts],  # type: ignore[union-attr]
                    "usage": resp.usage.model_dump() if resp.usage else {},
                    "secs": round(time.time() - t0, 1),
                }
                break
            except Exception as e:  # noqa: BLE001 - any failure is retried, then recorded
                rec = {"chunk": chunk_key, "verdicts": None, "error": str(e)[:300]}
                time.sleep(2 * (attempt + 1))
        with lock, out_path.open("a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    todo = [(k, i) for k, i in chunks if k not in done]
    if todo:
        first = call(*todo[0])  # warm the cache before fanning out
        if first.get("verdicts") is not None:
            done[first["chunk"]] = first
        with cf.ThreadPoolExecutor(int(os.environ.get("CONC", "8"))) as ex:
            for rec in ex.map(lambda ki: call(*ki), todo[1:]):
                if rec.get("verdicts") is not None:
                    done[rec["chunk"]] = rec
    print(
        f"== {variant} | {model} | effort {effort} | chunk {size} | chunks ok {len(done)}/{len(chunks)}"
    )
    score(gold, cands, done)
    report_usage(model, done)


def _predictions(
    by_key: dict, done: dict[str, dict]
) -> tuple[dict[str, str], dict[str, str]]:
    raw: dict[str, str] = {}
    rule: dict[str, str] = {}
    for rec in done.values():
        for v in rec["verdicts"]:
            if v["key"] not in by_key:
                continue
            cand, _ = by_key[v["key"]]
            kind = raw[v["key"]] = v["kind"]
            if kind in TRAPS and not is_trap(
                kind,
                same_root=v.get("same_root"),
                target_text=cand.target_text,
                known_text=cand.known_text,
            ):
                kind = "unrelated"
            rule[v["key"]] = kind
    return raw, rule


def score(
    gold: list[GoldPair], cands: list[LookalikeCandidate], done: dict[str, dict]
) -> None:
    """Print trap and cognate scores per gold origin, without and with the root rule."""
    by_key = {c.key: (c, g) for c, g in zip(cands, gold, strict=True)}
    raw, rule = _predictions(by_key, done)
    for label, pred in (("raw", raw), ("rule", rule)):
        for origin in ("all", "curated", "sampled-uniform", "sampled-close"):
            sel = [
                (k, g) for k, (_, g) in by_key.items() if origin in ("all", g.origin)
            ]
            n_trap = sum(g.kind in TRAPS for _, g in sel)
            found = sum(g.kind in TRAPS and pred.get(k) in TRAPS for k, g in sel)
            alarms = sum(g.kind not in TRAPS and pred.get(k) in TRAPS for k, g in sel)
            n_cog = sum(g.kind == "cognate" for _, g in sel)
            cog_found = sum(
                g.kind == "cognate" and pred.get(k) == "cognate" for k, g in sel
            )
            cog_pred = sum(pred.get(k) == "cognate" for k, _ in sel)
            exact = sum(
                pred.get(k) == ("unrelated" if g.kind == "noise" else g.kind)
                for k, g in sel
            )
            print(
                f"  {label:4} {origin:15} traps {found:3}/{n_trap:3}  false alarms {alarms:3}"
                f"  cognates {cog_found:3}/{n_cog:3} (precision {cog_found / cog_pred if cog_pred else 0:.2f})"
                f"  exact {exact / len(sel):.2f}  missing {sum(k not in pred for k, _ in sel)}"
            )


def report_usage(model: str, done: dict[str, dict]) -> None:
    """Print summed usage, cache reads and writes, and the live cost."""
    usage: Counter[str] = Counter()
    for rec in done.values():
        u = rec["usage"]
        details = u.get("prompt_tokens_details") or {}
        usage["input"] += u.get("prompt_tokens", 0)
        usage["cached"] += details.get("cached_tokens") or 0
        usage["write"] += details.get("cache_write_tokens") or 0
        usage["output"] += u.get("completion_tokens", 0)
    price_in, price_cached, price_out = PRICES[model]
    uncached = usage["input"] - usage["cached"] - usage["write"]
    cost = (
        uncached * price_in
        + usage["cached"] * price_cached
        + usage["write"] * price_in * 1.25
        + usage["output"] * price_out
    ) / 1e6
    no_cache = (usage["input"] * price_in + usage["output"] * price_out) / 1e6
    print(
        f"  usage {dict(usage)} | live cost ${cost:.4f} (without cache ${no_cache:.4f})"
    )


if __name__ == "__main__":
    main()
