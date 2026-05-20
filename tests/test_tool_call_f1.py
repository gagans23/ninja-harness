"""Tests for Tool Call F1 scorer."""

from __future__ import annotations

import pytest

from ninja_harness.schemas import AgentRun, EvaluationCase, ToolCall
from ninja_harness.scoring.tool_call_f1 import ToolCallF1Scorer


def make_run(*tool_names: str) -> AgentRun:
    return AgentRun(
        agent_name="A",
        task="t",
        final_output="out",
        tool_calls=[ToolCall(tool_name=n, arguments={}, status="success") for n in tool_names],
    )


def make_case(*tool_names: str) -> EvaluationCase:
    return EvaluationCase(
        task="t",
        expected_tool_calls=[
            ToolCall(tool_name=n, arguments={}, status="success") for n in tool_names
        ],
    )


@pytest.fixture
def scorer() -> ToolCallF1Scorer:
    return ToolCallF1Scorer()


def test_perfect_match(scorer: ToolCallF1Scorer) -> None:
    run = make_run("web_search", "read_file")
    case = make_case("web_search", "read_file")
    result = scorer.score(run, case)
    assert result.score == pytest.approx(1.0)
    assert result.passed is True


def test_no_expected(scorer: ToolCallF1Scorer) -> None:
    run = make_run("web_search")
    result = scorer.score(run, None)
    assert result.score == -1.0  # not applicable


def test_empty_actual(scorer: ToolCallF1Scorer) -> None:
    run = make_run()
    case = make_case("web_search", "read_file")
    result = scorer.score(run, case)
    assert result.score == 0.0
    assert result.passed is False


def test_empty_expected(scorer: ToolCallF1Scorer) -> None:
    run = make_run("web_search")
    case = EvaluationCase(task="t", expected_tool_calls=[])
    result = scorer.score(run, case)
    assert result.score == -1.0  # not applicable


def test_partial_match(scorer: ToolCallF1Scorer) -> None:
    run = make_run("web_search")
    case = make_case("web_search", "read_file")
    result = scorer.score(run, case)
    assert 0.0 < result.score < 1.0


def test_extra_tools_penalise_precision(scorer: ToolCallF1Scorer) -> None:
    run = make_run("web_search", "read_file", "write_file")
    case = make_case("web_search")
    result = scorer.score(run, case)
    assert result.score < 1.0


def test_argument_mismatch_is_partial(scorer: ToolCallF1Scorer) -> None:
    run = AgentRun(
        agent_name="A",
        task="t",
        final_output="out",
        tool_calls=[ToolCall(tool_name="web_search", arguments={"query": "different query"}, status="success")],
    )
    case = EvaluationCase(
        task="t",
        expected_tool_calls=[ToolCall(tool_name="web_search", arguments={"query": "expected query"}, status="success")],
    )
    result = scorer.score(run, case)
    # Name matches but args differ — should be a partial match, F1 > 0
    assert result.score > 0.0


def test_details_contain_counts(scorer: ToolCallF1Scorer) -> None:
    run = make_run("web_search")
    case = make_case("web_search")
    result = scorer.score(run, case)
    assert "precision" in result.details
    assert "recall" in result.details
    assert "f1" in result.details
