"""Tests for trajectory export (graded runs → training-ready JSONL)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import ninja_harness
from ninja_harness.export import (
    build_example,
    compress_run,
    export_runs,
    qualifies,
    to_messages,
    write_jsonl,
)
from ninja_harness.runner import EvaluationRunner
from ninja_harness.schemas import (
    AgentRun,
    AgentStep,
    EvaluationResult,
    ToolCall,
)

_EXAMPLES = Path(ninja_harness.__file__).parent / "examples"


def _run(**kw) -> AgentRun:
    base = dict(
        agent_name="researcher", task="find the capital of France",
        final_output="The capital of France is Paris.",
        steps=[
            AgentStep(agent_name="researcher", step_type="plan", output="Search for it."),
            AgentStep(agent_name="researcher", step_type="observation", output="Found a source."),
            AgentStep(agent_name="researcher", step_type="final",
                      output="The capital of France is Paris."),
        ],
        tool_calls=[ToolCall(tool_name="web_search", arguments={"q": "capital France"},
                             result="Paris", status="success")],
    )
    base.update(kw)
    return AgentRun(**base)


def _result(score=92.0, cert="PASS", run_id="r1") -> EvaluationResult:
    return EvaluationResult(run_id=run_id, ninja_score=score, grade="A", certification=cert)


# --- to_messages -----------------------------------------------------------


def test_to_messages_shape() -> None:
    msgs = to_messages(_run())
    assert msgs[0] == {"role": "user", "content": "find the capital of France"}
    # the 'plan' step is included; the 'final'-type / duplicate step is not
    assert {"role": "assistant", "content": "Search for it."} in msgs
    assert sum(1 for m in msgs if m["content"] == "The capital of France is Paris.") == 1
    # a tool call becomes an assistant tool_calls turn + a tool result turn
    tool_turn = next(m for m in msgs if m.get("tool_calls"))
    assert tool_turn["tool_calls"][0]["function"]["name"] == "web_search"
    assert any(m["role"] == "tool" and m["content"] == "Paris" for m in msgs)
    # final assistant turn is last
    assert msgs[-1] == {"role": "assistant", "content": "The capital of France is Paris."}


# --- compression -----------------------------------------------------------


def test_compress_run_drops_observations_and_caps_steps() -> None:
    r = compress_run(_run(), drop_observations=True)
    assert all(s.step_type != "observation" for s in r.steps)
    # original is untouched (pure copy)
    assert any(s.step_type == "observation" for s in _run().steps)
    capped = compress_run(_run(), max_steps=1)
    assert len(capped.steps) == 1
    # task, final, and tool calls always survive compression
    assert capped.final_output == "The capital of France is Paris."
    assert len(capped.tool_calls) == 1


# --- build_example ---------------------------------------------------------


def test_build_example_messages_and_sft() -> None:
    ex = build_example(_run(), _result(), fmt="messages")
    assert ex.format == "messages" and ex.messages and ex.ninja_score == 92.0
    assert ex.certification == "PASS" and ex.metadata["num_tool_calls"] == 1

    sft = build_example(_run(), _result(), fmt="sft")
    assert sft.format == "sft"
    assert sft.prompt == "find the capital of France"
    assert sft.completion == "The capital of France is Paris."


def test_build_example_rejects_unknown_format() -> None:
    with pytest.raises(ValueError):
        build_example(_run(), _result(), fmt="parquet")


# --- filtering + export_runs ----------------------------------------------


def test_qualifies_respects_pass_and_score() -> None:
    assert qualifies(_result(95, "PASS"), min_score=90, require_pass=True)
    assert not qualifies(_result(95, "WARN"), require_pass=True)
    assert qualifies(_result(95, "WARN"), require_pass=False)
    assert not qualifies(_result(70, "PASS"), min_score=80)


def test_export_runs_filters_and_summarizes() -> None:
    pairs = [
        (_run(run_id="r1"), _result(95, "PASS", "r1")),
        (_run(run_id="r2"), _result(60, "FAIL", "r2")),
        (_run(run_id="r3"), _result(88, "WARN", "r3")),
    ]
    examples, summary = export_runs(pairs, require_pass=True, min_score=0.0)
    assert summary.total_candidates == 3
    assert summary.exported == 1 and summary.skipped == 2  # only the PASS
    assert summary.by_certification == {"PASS": 1, "FAIL": 1, "WARN": 1}
    assert examples[0].run_id == "r1"

    # relax: keep PASS+WARN above 80
    ex2, sum2 = export_runs(pairs, require_pass=False, min_score=80.0)
    assert sum2.exported == 2  # 95/PASS and 88/WARN


# --- write_jsonl -----------------------------------------------------------


def test_write_jsonl_roundtrip(tmp_path) -> None:
    examples, _ = export_runs([(_run(run_id="r1"), _result())], require_pass=False)
    out = write_jsonl(examples, tmp_path / "sub" / "traj.jsonl")
    assert out.exists()
    lines = out.read_text().strip().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["run_id"] == "r1" and rec["format"] == "messages" and rec["messages"]


# --- integration: real evaluate → export ----------------------------------


def test_export_from_real_evaluation() -> None:
    run, _case, result = EvaluationRunner().run_from_files(
        _EXAMPLES / "simple_agent_trace.json", _EXAMPLES / "evaluation_case.yaml",
    )
    examples, summary = export_runs([(run, result)], require_pass=False)
    assert summary.total_candidates == 1 and summary.exported == 1
    ex = examples[0]
    assert ex.task and ex.messages
    assert ex.messages[0]["role"] == "user"
    assert ex.ninja_score == result.ninja_score
