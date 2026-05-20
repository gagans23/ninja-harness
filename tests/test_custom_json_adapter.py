"""Tests for CustomJsonAdapter."""

from __future__ import annotations

import pytest

from ninja_harness.adapters.custom_json import CustomJsonAdapter
from ninja_harness.schemas import AgentRun


@pytest.fixture
def adapter() -> CustomJsonAdapter:
    return CustomJsonAdapter()


@pytest.fixture
def minimal_trace() -> dict:
    return {
        "agent_name": "TestAgent",
        "task": "Do something",
        "final_output": "Done.",
    }


@pytest.fixture
def full_trace() -> dict:
    return {
        "run_id": "run-test-001",
        "agent_name": "ResearchAgent",
        "task": "Summarize AI research",
        "final_output": "Summary: transformers improved significantly.",
        "expected_output": "Transformers improved.",
        "steps": [
            {
                "step_id": "s1",
                "agent_name": "ResearchAgent",
                "step_type": "plan",
                "output": "Plan: search, synthesize.",
                "status": "completed",
            }
        ],
        "tool_calls": [
            {
                "tool_name": "web_search",
                "arguments": {"query": "AI research 2024"},
                "result": "Found papers.",
                "status": "success",
            }
        ],
        "handoffs": [],
        "guardrail_events": [],
    }


def test_can_parse_minimal(adapter: CustomJsonAdapter, minimal_trace: dict) -> None:
    assert adapter.can_parse(minimal_trace) is True


def test_cannot_parse_missing_fields(adapter: CustomJsonAdapter) -> None:
    assert adapter.can_parse({"agent_name": "A"}) is False
    assert adapter.can_parse({}) is False


def test_parse_minimal(adapter: CustomJsonAdapter, minimal_trace: dict) -> None:
    run = adapter.parse(minimal_trace)
    assert isinstance(run, AgentRun)
    assert run.agent_name == "TestAgent"
    assert run.task == "Do something"
    assert run.final_output == "Done."
    assert run.steps == []
    assert run.tool_calls == []


def test_parse_full_trace(adapter: CustomJsonAdapter, full_trace: dict) -> None:
    run = adapter.parse(full_trace)
    assert run.run_id == "run-test-001"
    assert len(run.steps) == 1
    assert run.steps[0].step_type == "plan"
    assert len(run.tool_calls) == 1
    assert run.tool_calls[0].tool_name == "web_search"
    assert run.tool_calls[0].status == "success"


def test_parse_generates_run_id_if_missing(adapter: CustomJsonAdapter, minimal_trace: dict) -> None:
    run = adapter.parse(minimal_trace)
    assert run.run_id != ""


def test_parse_run_id_preserved(adapter: CustomJsonAdapter, full_trace: dict) -> None:
    run = adapter.parse(full_trace)
    assert run.run_id == "run-test-001"


def test_parse_failed_step(adapter: CustomJsonAdapter) -> None:
    trace = {
        "agent_name": "A",
        "task": "t",
        "final_output": "out",
        "steps": [
            {
                "step_id": "s1",
                "agent_name": "A",
                "step_type": "action",
                "status": "failed",
                "error": "Something went wrong",
            }
        ],
    }
    run = adapter.parse(trace)
    assert run.failed_steps[0].error == "Something went wrong"


def test_parse_with_handoff(adapter: CustomJsonAdapter) -> None:
    trace = {
        "agent_name": "Orchestrator",
        "task": "task",
        "final_output": "done",
        "handoffs": [
            {
                "source_agent": "Orchestrator",
                "target_agent": "SubAgent",
                "reason": "delegation",
                "context_summary": "context here",
                "expected_next_action": "do the thing",
                "task_id": "t1",
                "trace_id": "tr1",
            }
        ],
    }
    run = adapter.parse(trace)
    assert len(run.handoffs) == 1
    assert run.handoffs[0].task_id == "t1"
