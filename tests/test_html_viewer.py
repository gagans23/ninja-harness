"""Tests for the self-contained HTML trace viewer."""

from __future__ import annotations

from ninja_harness.reporters import render_html
from ninja_harness.schemas import (
    AgentRun,
    AgentStep,
    EvaluationResult,
    Handoff,
    MetricResult,
    ToolCall,
)


def make_run(final: str = "All done.") -> AgentRun:
    return AgentRun(
        run_id="run-html",
        agent_name="ViewerAgent",
        task="Do the thing",
        final_output=final,
        steps=[AgentStep(agent_name="ViewerAgent", step_type="plan", output="planning")],
        tool_calls=[ToolCall(tool_name="search", arguments={"q": "x"}, result="found", status="success")],
        handoffs=[Handoff(source_agent="A", target_agent="B", reason="r", context_summary="c", expected_next_action="n")],
    )


def test_render_is_self_contained_html() -> None:
    html = render_html(make_run())
    assert html.startswith("<!DOCTYPE html>")
    assert "<style>" in html  # inline CSS, no external stylesheet
    assert 'src="http' not in html  # no external scripts/assets


def test_render_includes_trajectory_and_tools() -> None:
    html = render_html(make_run())
    assert "ViewerAgent" in html
    assert "search" in html
    assert "Handoffs" in html
    assert "Final Output" in html


def test_render_with_result_shows_metrics() -> None:
    result = EvaluationResult(
        run_id="run-html",
        metric_results=[MetricResult(name="safety", score=1.0, passed=True)],
        ninja_score=88.0,
        grade="B",
        certification="PASS",
    )
    html = render_html(make_run(), result)
    assert "PASS" in html
    assert "88.0/100" in html
    assert "Metrics" in html


def test_render_escapes_untrusted_content() -> None:
    run = make_run(final="<script>alert('xss')</script>")
    html = render_html(run)
    assert "<script>alert" not in html  # raw script must be escaped
    assert "&lt;script&gt;" in html
