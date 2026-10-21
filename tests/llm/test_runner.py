"""Tests for the resumable chain runner (`lang_tools.llm.runner`)."""

import json
from pathlib import Path

from langchain_core.messages import AIMessage
from llm_core.chains.structured_chain import StructuredLLMChain
from llm_core.data_models.basemodel_kwargs import BaseModelKwargs
from llm_core.testing.fake_chat_model import FakeChatModelConfig
from pydantic import BaseModel

from lang_tools.llm.runner import BATCH_ENDPOINT
from lang_tools.llm.runner import batch_requests
from lang_tools.llm.runner import load_checkpoint
from lang_tools.llm.runner import parse_batch_output
from lang_tools.llm.runner import read_records
from lang_tools.llm.runner import run_chain
from lang_tools.llm.runner import strict_json_schema


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
        body = {"choices": [{"message": {"content": content}}]}
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
