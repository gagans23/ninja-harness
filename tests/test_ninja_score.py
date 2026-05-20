"""Tests for the Ninja Score aggregator and certification logic."""

from __future__ import annotations

import pytest

from ninja_harness.certification import compute_certification, compute_grade
from ninja_harness.schemas import AgentRun, EvaluationCase, ToolCall
from ninja_harness.scoring.ninja_score import NinjaScoreAggregator


def clean_run() -> AgentRun:
    return AgentRun(
        agent_name="TestAgent",
        task="Summarize transformer research.",
        final_output=(
            "Transformers improved via FlashAttention, MoE routing, and speculative decoding. "
            "Quantization methods including AWQ reduce deployment cost."
        ),
        expected_output="Key advances: FlashAttention, MoE, speculative decoding, AWQ quantization.",
        tool_calls=[
            ToolCall(
                tool_name="web_search",
                arguments={"query": "transformer research 2024"},
                status="success",
                result="Found papers on FlashAttention and MoE.",
            )
        ],
    )


def clean_case() -> EvaluationCase:
    return EvaluationCase(
        task="Summarize transformer research.",
        expected_output="Key advances: FlashAttention, MoE, speculative decoding, AWQ quantization.",
        expected_tool_calls=[
            ToolCall(
                tool_name="web_search",
                arguments={"query": "transformer research 2024"},
                status="success",
            )
        ],
        references=[
            "FlashAttention reduces memory usage for transformers.",
            "MoE routing reduces per-token compute for large models.",
            "Speculative decoding speeds up inference without quality loss.",
            "AWQ quantization enables 4-bit inference with minimal degradation.",
        ],
    )


@pytest.fixture
def aggregator() -> NinjaScoreAggregator:
    return NinjaScoreAggregator()


def test_returns_evaluation_result(aggregator: NinjaScoreAggregator) -> None:
    from ninja_harness.schemas import EvaluationResult
    result = aggregator.evaluate(clean_run(), clean_case())
    assert isinstance(result, EvaluationResult)


def test_ninja_score_in_range(aggregator: NinjaScoreAggregator) -> None:
    result = aggregator.evaluate(clean_run(), clean_case())
    assert 0.0 <= result.ninja_score <= 100.0


def test_clean_run_gets_positive_score(aggregator: NinjaScoreAggregator) -> None:
    result = aggregator.evaluate(clean_run(), clean_case())
    assert result.ninja_score > 30.0


def test_all_metrics_present(aggregator: NinjaScoreAggregator) -> None:
    result = aggregator.evaluate(clean_run(), clean_case())
    metric_names = {m.name for m in result.metric_results}
    expected = {
        "goal_success",
        "tool_call_f1",
        "handoff_integrity",
        "grounding",
        "safety",
        "efficiency",
        "recovery",
        "stability",
    }
    assert metric_names == expected


def test_grade_a_for_high_score() -> None:
    assert compute_grade(95.0) == "A"
    assert compute_grade(90.0) == "A"


def test_grade_b_for_mid_score() -> None:
    assert compute_grade(85.0) == "B"
    assert compute_grade(80.0) == "B"


def test_grade_f_for_low_score() -> None:
    assert compute_grade(50.0) == "F"
    assert compute_grade(0.0) == "F"


def test_certification_pass() -> None:
    assert compute_certification(85.0, 0.9) == "PASS"


def test_certification_warn() -> None:
    assert compute_certification(65.0, 0.9) == "WARN"


def test_certification_fail_low_score() -> None:
    assert compute_certification(55.0, 0.9) == "FAIL"


def test_certification_fail_low_safety() -> None:
    assert compute_certification(85.0, 0.3) == "FAIL"


def test_certification_warn_decent_score_poor_safety() -> None:
    assert compute_certification(70.0, 0.6) == "WARN"


def test_run_without_case_still_scores(aggregator: NinjaScoreAggregator) -> None:
    result = aggregator.evaluate(clean_run(), case=None)
    assert result.ninja_score >= 0.0
    assert result.certification in {"PASS", "WARN", "FAIL"}
