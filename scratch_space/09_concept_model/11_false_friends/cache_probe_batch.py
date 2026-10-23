"""Check whether prompt caching applies inside an OpenAI Batch API job.

Six requests share a static prefix of more than 1024 tokens: p0-p2 use the
implicit cache mode, p3-p5 an explicit breakpoint after the static system text.
The submitted batch id is kept in ``batch_probe_id.txt`` next to this script.

Usage:
    uv run python cache_probe_batch.py submit   # writes a new batch id
    uv run python cache_probe_batch.py check    # prints status and per-request cache usage
"""

import json
from pathlib import Path
import sys

from openai import OpenAI

HERE = Path(__file__).parent
REPO = HERE.parents[2]
ID_FILE = HERE / "batch_probe_id.txt"
IN_FILE = HERE / "batch_probe_in.jsonl"
N_IMPLICIT = 3


def _static_prefix() -> str:
    v5 = (REPO / "src/lang_tools/prompts/lookalike_verify/v5.jinja").read_text()
    static = v5[: v5.index("Pairs (key")]
    doubled = static + "\n" + static  # v5's static part alone is ~800 tokens
    return (
        doubled.replace("{{ target_language_name }}", "the target").replace(
            "{{ known_language_name }}", "the known"
        )
        + "\nBatch probe."
    )


def submit(client: OpenAI) -> None:
    """Write the six requests and submit them as one batch."""
    static = _static_prefix()
    with IN_FILE.open("w") as f:
        for i in range(2 * N_IMPLICIT):
            explicit = i >= N_IMPLICIT
            block: dict = {"type": "text", "text": static}
            if explicit:
                block["prompt_cache_breakpoint"] = {"mode": "explicit"}
            body: dict = {
                "model": "gpt-6-luna",
                "reasoning_effort": "none",
                "messages": [
                    {"role": "system", "content": [block]},
                    {"role": "user", "content": f"Item {i}. Answer: ok"},
                ],
            }
            if explicit:
                body["prompt_cache_options"] = {"mode": "explicit"}
            row = {
                "custom_id": f"p{i}",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": body,
            }
            f.write(json.dumps(row) + "\n")
    with IN_FILE.open("rb") as f:
        file_id = client.files.create(file=f, purpose="batch").id
    batch = client.batches.create(
        input_file_id=file_id, endpoint="/v1/chat/completions", completion_window="24h"
    )
    ID_FILE.write_text(batch.id + "\n")
    print(batch.id, batch.status)


def check(client: OpenAI) -> None:
    """Print the batch status and, once done, each request's cache usage."""
    batch = client.batches.retrieve(ID_FILE.read_text().strip())
    print(batch.status, batch.request_counts)
    if batch.output_file_id:
        for line in client.files.content(batch.output_file_id).text.splitlines():
            row = json.loads(line)
            usage = row["response"]["body"]["usage"]
            print(
                row["custom_id"], usage["prompt_tokens"], usage["prompt_tokens_details"]
            )
    if batch.error_file_id:
        print(client.files.content(batch.error_file_id).text[:1000])


if __name__ == "__main__":
    (submit if sys.argv[1] == "submit" else check)(OpenAI())
