"""Tests for the statistical reliability module."""

from __future__ import annotations

import pytest

from ninja_harness.schemas import EvaluationResult, MetricResult
from ninja_harness.statistics import (
    aggregate_results,
    confidence_interval_95,
    consistency,
    mean,
    pass_at_k,
    pass_hat_k,
    stdev,
)


def make_result(score: float, cert: str, safety: float = 1.0) -> EvaluationResult:
    return EvaluationResult(
        run_id=f"run-{score}",
        metric_results=[MetricResult(name="safety", score=safety, passed=safety >= 0.8)],
        ninja_score=score,
        grade="A" if score >= 90 else "C",
        certification=cert,
    )


def test_mean_and_stdev() -> None:
    assert mean([10, 20, 30]) == 20
    assert stdev([10, 20, 30]) == pytest.approx(10.0)
    assert stdev([5]) == 0.0


def test_confidence_interval_single_value() -> None:
    low, high = confidence_interval_95([42.0])
    assert low == high == 42.0


def test_confidence_interval_brackets_mean() -> None:
    low, high = confidence_interval_95([80, 82, 78, 81, 79])
    assert low < 80 < high


def test_pass_at_k_and_hat_k() -> None:
    assert pass_at_k([False, True, False]) == 1.0
    assert pass_at_k([False, False]) == 0.0
    assert pass_hat_k([True, True, True]) == 1.0
    assert pass_hat_k([True, False, True]) == 0.0


def test_consistency_identical_scores() -> None:
    assert consistency([85, 85, 85]) == 1.0


def test_consistency_drops_with_variance() -> None:
    assert consistency([10, 90, 50]) < 1.0


def test_aggregate_reliable() -> None:
    results = [make_result(92, "PASS"), make_result(91, "PASS"), make_result(93, "PASS")]
    agg = aggregate_results(results, task_label="t")
    assert agg.reliability.trials == 3
    assert agg.reliability.pass_hat_k == 1.0
    assert agg.verdict == "RELIABLE"
    assert agg.reliability.certification_distribution["PASS"] == 3


def test_aggregate_flaky() -> None:
    results = [make_result(92, "PASS"), make_result(55, "FAIL"), make_result(90, "PASS")]
    agg = aggregate_results(results, task_label="t")
    assert agg.reliability.pass_at_k == 1.0
    assert agg.reliability.pass_hat_k == 0.0
    assert agg.verdict == "FLAKY"


def test_aggregate_unreliable() -> None:
    results = [make_result(40, "FAIL"), make_result(50, "FAIL")]
    agg = aggregate_results(results, task_label="t")
    assert agg.reliability.pass_at_k == 0.0
    assert agg.verdict == "UNRELIABLE"


def test_aggregate_per_metric_mean() -> None:
    results = [make_result(90, "PASS", safety=1.0), make_result(90, "PASS", safety=0.8)]
    agg = aggregate_results(results, task_label="t")
    assert agg.per_metric_mean["safety"] == pytest.approx(0.9)


def test_aggregate_empty_raises() -> None:
    with pytest.raises(ValueError):
        aggregate_results([], task_label="t")
