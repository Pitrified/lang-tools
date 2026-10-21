"""Run a structured chain over a worklist, resumably, live or through a batch.

Phase 8's maintenance jobs range from a handful of items (gloss repair) to
~174k (non-en gloss backfill). Both paths here write the same **checkpoint**: a
JSONL file with one `RunRecord` per finished item, appended as each item
completes. The checkpoint is the run's only state, so

- a killed run resumes where it stopped and never re-bills a finished item;
- every result carries the model, a hash of the exact prompt template and a
  timestamp, which is what makes an accepted row auditable later (phase 10's
  dataset card);
- the live and batch paths are interchangeable: a job can start live on a sample,
  then finish the rest through a batch, and `load_checkpoint` reads both;
- every record carries its measured token `Usage` (input, cached input, output,
  and the reasoning share of the output), so `summarize_usage` turns any
  checkpoint into measured totals and `UsageTotals.cost` prices them. A sample
  run is how a large job gets a real estimate before it is submitted.

Live path: `run_chain` calls `StructuredLLMChain.invoke` with bounded
concurrency. Batch path: `batch_requests` renders the chain's own prompt and the
output model as a strict JSON schema into OpenAI Batch API requests (pure, so it
is tested without a network); `submit_batch` / `collect_batch` are the thin
impure halves. Batch requests cost half and are the right path for anything
beyond a few thousand items.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
import copy
from datetime import UTC
from datetime import datetime
import hashlib
import json
from typing import TYPE_CHECKING
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from loguru import logger as lg
from pydantic import BaseModel

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Sequence
    from pathlib import Path

    from llm_core.chains.structured_chain import StructuredLLMChain
    from llm_core.data_models.basemodel_kwargs import BaseModelKwargs

#: Endpoint the batch requests target (structured outputs via chat completions).
BATCH_ENDPOINT = "/v1/chat/completions"


class Usage(BaseModel):
    """Measured token usage of one model call.

    Attributes:
        input_tokens: Prompt tokens billed (including the cached ones).
        cached_tokens: The part of `input_tokens` served from the prompt cache.
        output_tokens: Completion tokens billed (including reasoning).
        reasoning_tokens: The hidden-reasoning part of `output_tokens`.
    """

    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0


class UsageTotals(BaseModel):
    """Summed `Usage` over a checkpoint.

    Attributes:
        records: Records counted (failed ones included: they are billed too).
        with_usage: Records that carried a measured `Usage`.
        input_tokens: Summed input tokens.
        cached_tokens: Summed cached input tokens.
        output_tokens: Summed output tokens.
        reasoning_tokens: Summed reasoning tokens.
    """

    records: int = 0
    with_usage: int = 0
    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0

    def cost(
        self,
        *,
        input_per_m: float,
        output_per_m: float,
        cached_per_m: float | None = None,
    ) -> float:
        """Price the totals in dollars, given per-1M-token prices.

        Prices are arguments, not a table in code: they change, and a stale
        price baked in here would make every estimate quietly wrong.

        Args:
            input_per_m: Price of 1M uncached input tokens.
            output_per_m: Price of 1M output tokens (reasoning is billed as output).
            cached_per_m: Price of 1M cached input tokens; ``None`` bills them as
                uncached input.

        Returns:
            The cost in dollars.
        """
        cached_price = input_per_m if cached_per_m is None else cached_per_m
        uncached = self.input_tokens - self.cached_tokens
        return (
            uncached * input_per_m
            + self.cached_tokens * cached_price
            + self.output_tokens * output_per_m
        ) / 1e6


class RunRecord(BaseModel):
    """One finished item in a checkpoint (a JSONL line).

    Attributes:
        key: The worklist item's stable key.
        output: The chain output, as a plain dict (``None`` when it failed).
        error: The failure message, when the item failed.
        model: Model name the item ran on.
        prompt_sha: First 12 hex chars of the prompt template's SHA-1, so a
            result names the exact prompt that produced it.
        path: ``live`` or ``batch``.
        at: UTC timestamp the record was written.
        usage: Measured token usage of the call, when the provider reported it
            (``None`` on records written before usage was tracked).
    """

    key: str
    output: dict[str, Any] | None = None
    error: str | None = None
    model: str
    prompt_sha: str
    path: str
    at: datetime
    usage: Usage | None = None


def usage_from_openai(raw: dict[str, Any] | None) -> Usage | None:
    """Read a `Usage` from an OpenAI ``usage`` object (chat completions shape)."""
    if not raw:
        return None
    prompt_details = raw.get("prompt_tokens_details") or {}
    completion_details = raw.get("completion_tokens_details") or {}
    return Usage(
        input_tokens=int(raw.get("prompt_tokens") or 0),
        cached_tokens=int(prompt_details.get("cached_tokens") or 0),
        output_tokens=int(raw.get("completion_tokens") or 0),
        reasoning_tokens=int(completion_details.get("reasoning_tokens") or 0),
    )


class _UsageCallback(BaseCallbackHandler):
    """Collect the usage LangChain attaches to a chat model's response."""

    def __init__(self) -> None:
        self.usage = Usage()
        self.seen = False

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:  # noqa: ANN401, ARG002
        """Add the usage of each generation's message (LangChain usage_metadata)."""
        for generations in getattr(response, "generations", []):
            for generation in generations:
                message = getattr(generation, "message", None)
                meta = getattr(message, "usage_metadata", None)
                if not meta:
                    continue
                self.seen = True
                self.usage.input_tokens += int(meta.get("input_tokens", 0) or 0)
                self.usage.output_tokens += int(meta.get("output_tokens", 0) or 0)
                in_details = meta.get("input_token_details") or {}
                out_details = meta.get("output_token_details") or {}
                self.usage.cached_tokens += int(in_details.get("cache_read", 0) or 0)
                self.usage.reasoning_tokens += int(out_details.get("reasoning", 0) or 0)


def summarize_usage(records: Iterable[RunRecord]) -> UsageTotals:
    """Sum the measured usage of every record (failed calls are billed too)."""
    totals = UsageTotals()
    for record in records:
        totals.records += 1
        if record.usage is None:
            continue
        totals.with_usage += 1
        totals.input_tokens += record.usage.input_tokens
        totals.cached_tokens += record.usage.cached_tokens
        totals.output_tokens += record.usage.output_tokens
        totals.reasoning_tokens += record.usage.reasoning_tokens
    return totals


def prompt_sha(chain: StructuredLLMChain[Any, Any]) -> str:
    """Return the 12-char SHA-1 of a chain's prompt template."""
    digest = hashlib.sha1(chain.prompt_str.encode("utf-8"), usedforsecurity=False)
    return digest.hexdigest()[:12]


def read_records(checkpoint: Path) -> list[RunRecord]:
    """Read every record in a checkpoint (empty when it does not exist yet)."""
    if not checkpoint.exists():
        return []
    with checkpoint.open("r", encoding="utf-8") as fh:
        return [RunRecord.model_validate_json(line) for line in fh if line.strip()]


def load_checkpoint[OutputT: BaseModel](
    checkpoint: Path,
    output_model: type[OutputT],
) -> dict[str, OutputT]:
    """Return the successful outputs in a checkpoint, keyed by item key.

    A key that appears more than once keeps its latest success; failed records
    are skipped, so a re-run retries them.
    """
    outputs: dict[str, OutputT] = {}
    for record in read_records(checkpoint):
        if record.output is not None:
            outputs[record.key] = output_model.model_validate(record.output)
    return outputs


def _append(checkpoint: Path, record: RunRecord) -> None:
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    with checkpoint.open("a", encoding="utf-8") as fh:
        fh.write(record.model_dump_json() + "\n")


def run_chain[InputT: BaseModelKwargs, OutputT: BaseModel](
    chain: StructuredLLMChain[InputT, OutputT],
    items: Iterable[tuple[str, InputT]],
    *,
    checkpoint: Path,
    concurrency: int = 4,
    limit: int | None = None,
) -> dict[str, OutputT]:
    """Run `chain` live over the items the checkpoint does not hold yet.

    Args:
        chain: The structured chain to run.
        items: ``(key, input)`` pairs; keys must be unique and stable across runs.
        checkpoint: JSONL checkpoint path; created on first write.
        concurrency: Worker threads (the calls are network-bound).
        limit: Run at most this many new items (a sample run before a batch).

    Returns:
        Every successful output in the checkpoint after the run, old and new.
    """
    done = load_checkpoint(checkpoint, chain.output_model)
    todo = [(key, item) for key, item in items if key not in done]
    if limit is not None:
        todo = todo[:limit]
    lg.info("{} item(s) already done, running {}", len(done), len(todo))
    model = str(getattr(chain.chat_config, "model", "unknown"))
    sha = prompt_sha(chain)

    def _one(key: str, item: InputT) -> RunRecord:
        # The callback is the one place LangChain still exposes token usage once
        # with_structured_output has parsed the reply.
        callback = _UsageCallback()
        try:
            output = chain.chain.invoke(item.to_kw(), config={"callbacks": [callback]})
            if not isinstance(output, chain.output_model):
                msg = f"Unexpected output type: {type(output)}"
                raise TypeError(msg)  # noqa: TRY301 - recorded below like any failure
        except Exception as exc:  # noqa: BLE001 - recorded, retried on the next run
            return RunRecord(
                key=key,
                error=f"{type(exc).__name__}: {exc}",
                model=model,
                prompt_sha=sha,
                path="live",
                at=datetime.now(tz=UTC),
                usage=callback.usage if callback.seen else None,
            )
        return RunRecord(
            key=key,
            output=output.model_dump(),
            model=model,
            prompt_sha=sha,
            path="live",
            at=datetime.now(tz=UTC),
            usage=callback.usage if callback.seen else None,
        )

    failed = 0
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        futures = [pool.submit(_one, key, item) for key, item in todo]
        for future in as_completed(futures):
            record = future.result()
            _append(checkpoint, record)  # one writer: as_completed is this thread
            failed += record.error is not None
    if failed:
        lg.warning("{} item(s) failed; re-run to retry them", failed)
    return load_checkpoint(checkpoint, chain.output_model)


def strict_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Return `model`'s JSON schema in the shape OpenAI strict mode requires.

    Strict structured outputs need every property listed as required and
    ``additionalProperties: false`` on every object; pydantic omits both for
    fields with defaults. Applied recursively, including to ``$defs``.
    """
    schema = copy.deepcopy(model.model_json_schema())

    def _fix(node: Any) -> None:  # noqa: ANN401 - arbitrary JSON schema node
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                node["required"] = sorted(node["properties"])
                node["additionalProperties"] = False
            node.pop("default", None)
            for value in node.values():
                _fix(value)
        elif isinstance(node, list):
            for value in node:
                _fix(value)

    _fix(schema)
    return schema


def batch_requests[InputT: BaseModelKwargs, OutputT: BaseModel](
    chain: StructuredLLMChain[InputT, OutputT],
    items: Sequence[tuple[str, InputT]],
    *,
    extra_body: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Render Batch API request lines for `items` with `chain`'s own prompt.

    The system message is the chain's template rendered exactly as `invoke`
    renders it, and the response format is the chain's output model, so a batch
    result validates into the same model a live call returns.

    Args:
        chain: The structured chain whose prompt and output model to use.
        items: ``(key, input)`` pairs; the key becomes the request ``custom_id``.
        extra_body: Extra request-body fields merged into every request, e.g.
            ``{"reasoning_effort": "low"}`` for a reasoning model.

    Returns:
        One request dict per item, ready to be written as JSONL.
    """
    model = str(getattr(chain.chat_config, "model", "unknown"))
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": chain.output_model.__name__,
            "schema": strict_json_schema(chain.output_model),
            "strict": True,
        },
    }
    requests = []
    for key, item in items:
        messages = chain.prompt_template.format_messages(**item.to_kw())
        requests.append(
            {
                "custom_id": key,
                "method": "POST",
                "url": BATCH_ENDPOINT,
                "body": {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": str(m.content)} for m in messages
                    ],
                    "response_format": response_format,
                    **(extra_body or {}),
                },
            },
        )
    return requests


def parse_batch_output[OutputT: BaseModel](
    lines: Iterable[str],
    output_model: type[OutputT],
    *,
    model: str,
    sha: str,
) -> list[RunRecord]:
    """Turn Batch API output lines into checkpoint records (pure).

    A line whose response is not a 200, or whose content does not validate into
    `output_model`, becomes a failed record, so the next run retries it.
    """
    records = []
    for line in lines:
        if not line.strip():
            continue
        row = json.loads(line)
        key = row["custom_id"]
        response = row.get("response") or {}
        usage = usage_from_openai((response.get("body") or {}).get("usage"))
        try:
            if response.get("status_code") != 200:  # noqa: PLR2004 - HTTP OK
                raise ValueError(str(row.get("error") or response))  # noqa: TRY301
            content = response["body"]["choices"][0]["message"]["content"]
            output = output_model.model_validate_json(content).model_dump()
            records.append(
                RunRecord(
                    key=key,
                    output=output,
                    model=model,
                    prompt_sha=sha,
                    path="batch",
                    at=datetime.now(tz=UTC),
                    usage=usage,
                ),
            )
        except (KeyError, IndexError, ValueError) as exc:
            records.append(
                RunRecord(
                    key=key,
                    error=f"{type(exc).__name__}: {exc}",
                    model=model,
                    prompt_sha=sha,
                    path="batch",
                    at=datetime.now(tz=UTC),
                    usage=usage,
                ),
            )
    return records


def submit_batch[InputT: BaseModelKwargs, OutputT: BaseModel](
    chain: StructuredLLMChain[InputT, OutputT],
    items: Iterable[tuple[str, InputT]],
    *,
    checkpoint: Path,
    workdir: Path,
    extra_body: dict[str, Any] | None = None,
) -> str | None:
    """Upload the items the checkpoint does not hold yet as one OpenAI batch.

    Args:
        chain: The structured chain to run.
        items: ``(key, input)`` pairs.
        checkpoint: The job's checkpoint (finished keys are skipped).
        workdir: Where the request JSONL and the batch id are kept.
        extra_body: Extra request-body fields (see `batch_requests`).

    Returns:
        The batch id, or ``None`` when nothing is left to run.
    """
    from openai import OpenAI  # noqa: PLC0415 - only the batch path needs the SDK

    done = load_checkpoint(checkpoint, chain.output_model)
    todo = [(key, item) for key, item in items if key not in done]
    if not todo:
        lg.info("Nothing to submit: every item is in the checkpoint")
        return None
    workdir.mkdir(parents=True, exist_ok=True)
    request_path = workdir / "batch_requests.jsonl"
    with request_path.open("w", encoding="utf-8") as fh:
        for request in batch_requests(chain, todo, extra_body=extra_body):
            fh.write(json.dumps(request, ensure_ascii=False) + "\n")
    client = OpenAI()
    with request_path.open("rb") as fh:
        uploaded = client.files.create(file=fh, purpose="batch")
    batch = client.batches.create(
        input_file_id=uploaded.id,
        endpoint=BATCH_ENDPOINT,
        completion_window="24h",
    )
    (workdir / "batch_id.txt").write_text(batch.id, encoding="utf-8")
    lg.info("Submitted batch {} with {} request(s)", batch.id, len(todo))
    return batch.id


def collect_batch[InputT: BaseModelKwargs, OutputT: BaseModel](
    chain: StructuredLLMChain[InputT, OutputT],
    batch_id: str,
    *,
    checkpoint: Path,
) -> str:
    """Append a finished batch's results to the checkpoint; return its status.

    Safe to call repeatedly: until the batch is ``completed`` it only reports
    the status, and the results are written once, on completion.
    """
    from openai import OpenAI  # noqa: PLC0415 - only the batch path needs the SDK

    client = OpenAI()
    batch = client.batches.retrieve(batch_id)
    if batch.status != "completed":
        lg.info("Batch {} is {}", batch_id, batch.status)
        return batch.status
    lines: list[str] = []
    for file_id in (batch.output_file_id, batch.error_file_id):
        if file_id:
            lines.extend(client.files.content(file_id).text.splitlines())
    model = str(getattr(chain.chat_config, "model", "unknown"))
    records = parse_batch_output(
        lines,
        chain.output_model,
        model=model,
        sha=prompt_sha(chain),
    )
    for record in records:
        _append(checkpoint, record)
    failed = sum(record.error is not None for record in records)
    lg.info("Collected {} result(s) from {}, {} failed", len(records), batch_id, failed)
    return batch.status
