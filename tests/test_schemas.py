"""Tests for Pydantic schema models."""

from __future__ import annotations

from datetime import UTC

import pytest
from pydantic import ValidationError

from ninja_harness.schemas import (
    AgentRun,
    AgentStep,
    EvaluationCase,
    EvaluationResult,
    GuardrailEvent,
    Handoff,
    MetricResult,
    ToolCall,
)


def test_tool_call_defaults() -> None:
    tc = ToolCall(tool_name="web_search", arguments={"query": "test"})
    assert tc.status == "unknown"
    assert tc.result is None
    assert tc.error is None


def test_tool_call_required_field() -> None:
    with pytest.raises(ValidationError):
        ToolCall()  # type: ignore[call-arg]


def test_agent_step_defaults() -> None:
    step = AgentStep(agent_name="Agent", step_type="plan")
    assert step.status == "completed"
    assert step.step_id != ""


def test_handoff_fields() -> None:
    h = Handoff(
        source_agent="A",
        target_agent="B",
        reason="task delegation",
        context_summary="Doing X",
        expected_next_action="Do Y",
    )
    assert h.task_id is None
    assert h.trace_id is None
    assert h.metadata == {}


def test_guardrail_event() -> None:
    g = GuardrailEvent(
        guardrail_name="safety_check",
        status="passed",
        message="All good",
        severity="low",
    )
    assert g.guardrail_name == "safety_check"


def test_agent_run_defaults() -> None:
    run = AgentRun(
        agent_name="TestAgent",
        task="Do something",
        final_output="Done.",
    )
    assert run.run_id != ""
    assert run.steps == []
    assert run.tool_calls == []
    assert run.handoffs == []
    assert run.guardrail_events == []


def test_agent_run_latency_none() -> None:
    run = AgentRun(agent_name="A", task="t", final_output="out")
    assert run.latency_seconds is None


def test_agent_run_latency_computed() -> None:
    from datetime import datetime

    run = AgentRun(
        agent_name="A",
        task="t",
        final_output="out",
        start_time=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        end_time=datetime(2024, 1, 1, 0, 0, 30, tzinfo=UTC),
    )
    assert run.latency_seconds == 30.0


def test_evaluation_case_defaults() -> None:
    case = EvaluationCase(task="Test task")
    assert case.expected_tool_calls == []
    assert case.references == []
    assert case.safety_requirements == []


def test_metric_result_applicable() -> None:
    mr = MetricResult(name="goal_success", score=0.8, passed=True)
    assert mr.is_applicable is True


def test_metric_result_not_applicable() -> None:
    mr = MetricResult(name="handoff_integrity", score=-1.0, passed=True)
    assert mr.is_applicable is False


def test_evaluation_result_metric_by_name() -> None:
    mr = MetricResult(name="safety", score=1.0, passed=True)
    result = EvaluationResult(
        run_id="r1",
        metric_results=[mr],
        ninja_score=90.0,
        grade="A",
        certification="PASS",
    )
    assert result.metric_by_name("safety") == mr
    assert result.metric_by_name("nonexistent") is None
