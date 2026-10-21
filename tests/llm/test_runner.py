"""Tests for the resumable chain runner (`lang_tools.llm.runner`)."""

import json
from pathlib import Path

from langchain_core.messages import AIMessage
from llm_core.chains.structured_chain import StructuredLLMChain
from llm_core.data_models.basemodel_kwargs import BaseModelKwargs
from llm_core.testing.fake_chat_model import FakeChatModelConfig
import openai
from pydantic import BaseModel

from lang_tools.llm.runner import BATCH_ENDPOINT
from lang_tools.llm.runner import UsageTotals
from lang_tools.llm.runner import batch_requests
from lang_tools.llm.runner import load_checkpoint
from lang_tools.llm.runner import parse_batch_output
from lang_tools.llm.runner import read_records
from lang_tools.llm.runner import run_chain
from lang_tools.llm.runner import strict_json_schema
from lang_tools.llm.runner import submit_batch
from lang_tools.llm.runner import summarize_usage


class _In(BaseModelKwargs):
    word: str


class _Out(BaseModel):
    gloss: str
    note: str = ""


def _chain(*replies: str) -> StructuredLLMChain[_In, _Out]:
    return StructuredLLMChain(
        chat_config=FakeChatModelConfig(
            responses=[AIMessage(content=reply) for reply in replies],
        ),
        prompt_str="Define {{ word }}.",
        input_model=_In,
        output_model=_Out,
    )


def _items(*words: str) -> list[tuple[str, _In]]:
    return [(word, _In(word=word)) for word in words]


def test_run_writes_one_record_per_item(tmp_path: Path) -> None:
    checkpoint = tmp_path / "run.jsonl"
    chain = _chain('{"gloss": "g"}')
    outputs = run_chain(chain, _items("a", "b"), checkpoint=checkpoint, concurrency=1)
    assert set(outputs) == {"a", "b"}
    records = read_records(checkpoint)
    assert {r.key for r in records} == {"a", "b"}
    assert {r.path for r in records} == {"live"}
    assert all(r.model == "fake" and len(r.prompt_sha) == 12 for r in records)


def test_rerun_skips_finished_items(tmp_path: Path) -> None:
    checkpoint = tmp_path / "run.jsonl"
    run_chain(_chain('{"gloss": "g"}'), _items("a"), checkpoint=checkpoint)
    run_chain(_chain('{"gloss": "g"}'), _items("a", "b"), checkpoint=checkpoint)
    # 'a' is never re-run: one record for it, one for 'b'.
    assert sorted(r.key for r in read_records(checkpoint)) == ["a", "b"]


def test_failure_is_recorded_and_retried(tmp_path: Path) -> None:
    checkpoint = tmp_path / "run.jsonl"
    outputs = run_chain(_chain("not json"), _items("a"), checkpoint=checkpoint)
    assert outputs == {}
    assert read_records(checkpoint)[0].error is not None
    outputs = run_chain(_chain('{"gloss": "g"}'), _items("a"), checkpoint=checkpoint)
    assert outputs["a"].gloss == "g"


def test_limit_runs_a_sample(tmp_path: Path) -> None:
    checkpoint = tmp_path / "run.jsonl"
    outputs = run_chain(
        _chain('{"gloss": "g"}'),
        _items("a", "b", "c"),
        checkpoint=checkpoint,
        limit=2,
    )
    assert len(outputs) == 2


def test_strict_schema_requires_every_field() -> None:
    schema = strict_json_schema(_Out)
    assert schema["required"] == ["gloss", "note"]
    assert schema["additionalProperties"] is False
    assert "default" not in schema["properties"]["note"]


def test_batch_requests_render_the_chains_own_prompt() -> None:
    (request,) = batch_requests(_chain('{"gloss": "g"}'), _items("casa"))
    assert request["custom_id"] == "casa"
    assert request["url"] == BATCH_ENDPOINT
    body = request["body"]
    assert body["messages"] == [{"role": "system", "content": "Define casa."}]
    assert body["response_format"]["json_schema"]["strict"] is True


def test_batch_output_parses_and_flags_failures(tmp_path: Path) -> None:
    def _line(key: str, status: int, content: str) -> str:
        body = {
            "choices": [{"message": {"content": content}}],
            "usage": {
                "prompt_tokens": 100,
                "prompt_tokens_details": {"cached_tokens": 40},
                "completion_tokens": 30,
                "completion_tokens_details": {"reasoning_tokens": 20},
            },
        }
        return json.dumps(
            {"custom_id": key, "response": {"status_code": status, "body": body}},
        )

    records = parse_batch_output(
        [
            _line("a", 200, '{"gloss": "g", "note": ""}'),
            _line("b", 500, ""),
            _line("c", 200, "not json"),
        ],
        _Out,
        model="m",
        sha="0" * 12,
    )
    assert [(r.key, r.error is None) for r in records] == [
        ("a", True),
        ("b", False),
        ("c", False),
    ]
    checkpoint = tmp_path / "run.jsonl"
    checkpoint.write_text(
        "".join(r.model_dump_json() + "\n" for r in records),
        encoding="utf-8",
    )
    assert set(load_checkpoint(checkpoint, _Out)) == {"a"}
    totals = summarize_usage(records)
    assert (totals.records, totals.with_usage) == (3, 3)
    assert (totals.input_tokens, totals.cached_tokens) == (300, 120)
    assert (totals.output_tokens, totals.reasoning_tokens) == (90, 60)


def test_live_run_records_the_reported_usage(tmp_path: Path) -> None:
    reply = AIMessage(
        content='{"gloss": "g"}',
        usage_metadata={
            "input_tokens": 50,
            "output_tokens": 12,
            "total_tokens": 62,
            "input_token_details": {"cache_read": 10},
            "output_token_details": {"reasoning": 4},
        },
    )
    chain = StructuredLLMChain(
        chat_config=FakeChatModelConfig(responses=[reply]),
        prompt_str="Define {{ word }}.",
        input_model=_In,
        output_model=_Out,
    )
    checkpoint = tmp_path / "run.jsonl"
    run_chain(chain, _items("a"), checkpoint=checkpoint, concurrency=1)
    (record,) = read_records(checkpoint)
    assert record.usage is not None
    assert record.usage.model_dump() == {
        "input_tokens": 50,
        "cached_tokens": 10,
        "output_tokens": 12,
        "reasoning_tokens": 4,
    }


def test_usage_totals_price_cached_input_separately() -> None:
    totals = UsageTotals(
        input_tokens=2_000_000,
        cached_tokens=1_000_000,
        output_tokens=1_000_000,
    )
    # 1M uncached at $1 + 1M cached at $0.10 + 1M output at $4
    assert totals.cost(input_per_m=1, output_per_m=4, cached_per_m=0.1) == 5.1
    assert totals.cost(input_per_m=1, output_per_m=4) == 6.0


class _FakeBatches:
    def __init__(self, status: str) -> None:
        self.status = status
        self.created = 0

    def retrieve(self, batch_id: str) -> object:
        return type("B", (), {"id": batch_id, "status": self.status})()

    def create(self, **_kwargs: object) -> object:
        self.created += 1
        return type("B", (), {"id": "batch_new"})()


class _FakeFiles:
    def create(self, **_kwargs: object) -> object:
        return type("F", (), {"id": "file_1"})()


def _fake_client(monkeypatch, status: str) -> _FakeBatches:  # noqa: ANN001
    batches = _FakeBatches(status)
    client = type("C", (), {"batches": batches, "files": _FakeFiles()})()
    monkeypatch.setattr(openai, "OpenAI", lambda: client)
    return batches


def test_submit_never_pays_twice_for_a_live_batch(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    (tmp_path / "batch_id.txt").write_text("batch_old", encoding="utf-8")
    batches = _fake_client(monkeypatch, "in_progress")
    chain = _chain('{"gloss": "g"}')
    cp = tmp_path / "cp.jsonl"
    got = submit_batch(chain, _items("a"), checkpoint=cp, workdir=tmp_path)
    assert got == "batch_old"
    assert batches.created == 0


def test_submit_replaces_a_dead_batch(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    (tmp_path / "batch_id.txt").write_text("batch_old", encoding="utf-8")
    batches = _fake_client(monkeypatch, "expired")
    chain = _chain('{"gloss": "g"}')
    cp = tmp_path / "cp.jsonl"
    got = submit_batch(chain, _items("a"), checkpoint=cp, workdir=tmp_path)
    assert got == "batch_new"
    assert batches.created == 1
    assert (tmp_path / "batch_id.txt").read_text(encoding="utf-8") == "batch_new"
