"""Tests for evaluation policy gating."""

from __future__ import annotations

import json

import pytest

from ninja_harness.policy import apply_policy, load_policy
from ninja_harness.schemas import (
    EvaluationPolicy,
    EvaluationResult,
    MetricResult,
    MetricThreshold,
)


def make_result(score: float, cert: str, safety: float = 1.0) -> EvaluationResult:
    return EvaluationResult(
        run_id="r",
        metric_results=[MetricResult(name="safety", score=safety, passed=safety >= 0.8)],
        ninja_score=score,
        grade="B",
        certification=cert,
    )


def test_gate_passes_when_all_satisfied() -> None:
    result = make_result(90, "PASS")
    policy = EvaluationPolicy(min_ninja_score=85, required_certification="PASS")
    gate = apply_policy(result, policy)
    assert gate.passed is True
    assert gate.violations == []


def test_gate_fails_low_score() -> None:
    result = make_result(70, "WARN")
    policy = EvaluationPolicy(min_ninja_score=85)
    gate = apply_policy(result, policy)
    assert gate.passed is False
    assert any(v.rule == "min_ninja_score" for v in gate.violations)


def test_gate_fails_certification() -> None:
    result = make_result(82, "WARN")
    policy = EvaluationPolicy(required_certification="PASS")
    gate = apply_policy(result, policy)
    assert any(v.rule == "required_certification" for v in gate.violations)


def test_gate_metric_threshold() -> None:
    result = make_result(90, "PASS", safety=0.6)
    policy = EvaluationPolicy(metric_thresholds=[MetricThreshold(metric="safety", min_score=0.8)])
    gate = apply_policy(result, policy)
    assert any(v.rule == "metric_threshold:safety" for v in gate.violations)


def test_gate_regression_vs_baseline() -> None:
    baseline = make_result(90, "PASS")
    result = make_result(75, "WARN")
    policy = EvaluationPolicy(max_score_regression=10)
    gate = apply_policy(result, policy, baseline=baseline)
    assert any(v.rule == "max_score_regression" for v in gate.violations)


def test_gate_redteam_findings() -> None:
    result = make_result(90, "PASS")
    policy = EvaluationPolicy(fail_on_redteam_findings=True)
    findings = [{"check": "prompt_injection", "severity": "critical"}]
    gate = apply_policy(result, policy, redteam_findings=findings)
    assert any(v.rule == "fail_on_redteam_findings" for v in gate.violations)


def test_gate_min_safety_score() -> None:
    result = make_result(90, "PASS", safety=0.4)
    policy = EvaluationPolicy(min_safety_score=0.8)
    gate = apply_policy(result, policy)
    assert any(v.rule == "min_safety_score" for v in gate.violations)


def test_load_policy_yaml(tmp_path) -> None:
    p = tmp_path / "policy.yaml"
    p.write_text("name: test\nmin_ninja_score: 80\n")
    policy = load_policy(p)
    assert policy.name == "test"
    assert policy.min_ninja_score == 80


def test_load_policy_json(tmp_path) -> None:
    p = tmp_path / "policy.json"
    p.write_text(json.dumps({"name": "j", "required_certification": "PASS"}))
    policy = load_policy(p)
    assert policy.required_certification == "PASS"


def test_load_policy_missing_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_policy("nope.yaml")
