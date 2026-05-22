"""Tests for diff_results."""

from __future__ import annotations

from ninja_harness.diffing import diff_results
from ninja_harness.schemas import EvaluationResult, MetricResult


def make(run_id, score, cert, metrics):
    return EvaluationResult(
        run_id=run_id, ninja_score=score, grade="B", certification=cert,
        metric_results=[MetricResult(name=n, score=s, passed=s >= 0.5) for n, s in metrics],
    )


def test_score_and_cert_delta() -> None:
    base = make("r1", 80.0, "PASS", [("goal_success", 0.9), ("safety", 1.0)])
    curr = make("r2", 70.0, "WARN", [("goal_success", 0.7), ("safety", 1.0)])
    d = diff_results(base, curr)
    assert d.score_delta == -10.0
    assert d.certification_changed is True
    assert d.has_regression is True


def test_metric_status_classification() -> None:
    base = make("r1", 80, "PASS", [("goal_success", 0.5), ("safety", 1.0)])
    curr = make("r2", 85, "PASS", [("goal_success", 0.8), ("safety", 0.9)])
    d = diff_results(base, curr)
    by = {m.name: m for m in d.metric_deltas}
    assert by["goal_success"].status == "improved"
    assert by["safety"].status == "regressed"
    assert "goal_success" in d.improvements
    assert "safety" in d.regressions


def test_added_and_removed_metrics() -> None:
    base = make("r1", 80, "PASS", [("goal_success", 0.9)])
    curr = make("r2", 80, "PASS", [("goal_success", 0.9), ("grounding", 0.8)])
    d = diff_results(base, curr)
    by = {m.name: m for m in d.metric_deltas}
    assert by["grounding"].status == "added"


def test_na_metrics_ignored() -> None:
    base = make("r1", 80, "PASS", [("tool_call_f1", -1.0)])  # N/A
    curr = make("r2", 80, "PASS", [("tool_call_f1", -1.0)])
    d = diff_results(base, curr)
    assert {m.name: m for m in d.metric_deltas}["tool_call_f1"].status == "na"


def test_no_regression_when_improved() -> None:
    base = make("r1", 70, "WARN", [("goal_success", 0.6)])
    curr = make("r2", 90, "PASS", [("goal_success", 0.95)])
    d = diff_results(base, curr)
    assert d.has_regression is False
    assert d.score_delta == 20.0
