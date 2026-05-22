"""
Test helpers — assert agent quality from your own test suite.

These work with plain `pytest` (or unittest); the pytest *plugin*
(`ninja_harness.pytest_plugin`) wraps them in a fixture, but you can call them
directly too:

    from ninja_harness.testing import assert_agent, evaluate_trace

    def test_my_agent():
        assert_agent("traces/run.json", case="cases/case.yaml",
                     min_score=80, certification="PASS", min_safety=0.8)
"""

from __future__ import annotations

from pathlib import Path

from ninja_harness.adapters import detect_adapter
from ninja_harness.datasets.loader import load_eval_case, load_trace
from ninja_harness.schemas import EvaluationCase, EvaluationResult
from ninja_harness.scoring.judge import Judge
from ninja_harness.scoring.ninja_score import NinjaScoreAggregator

_CERT_RANK = {"FAIL": 0, "WARN": 1, "PASS": 2}


def evaluate_trace(
    trace: str | Path | dict,
    case: str | Path | dict | None = None,
    *,
    judge: Judge | None = None,
    baseline_path: str | None = None,
) -> EvaluationResult:
    """Evaluate a trace against an optional eval case. Both accept a path or a dict."""
    raw = trace if isinstance(trace, dict) else load_trace(trace)
    run = detect_adapter(raw).parse(raw)
    if case is None:
        case_obj = None
    elif isinstance(case, dict):
        case_obj = EvaluationCase.model_validate(case)
    else:
        case_obj = load_eval_case(case)
    return NinjaScoreAggregator(baseline_path=baseline_path, judge=judge).evaluate(run, case_obj)


def assert_agent(
    trace: str | Path | dict,
    case: str | Path | dict | None = None,
    *,
    min_score: float | None = None,
    certification: str | None = None,
    min_safety: float | None = None,
    max_failures: dict[str, float] | None = None,
    judge: Judge | None = None,
) -> EvaluationResult:
    """
    Evaluate a trace and assert quality thresholds. Raises AssertionError with a
    readable message on failure; returns the EvaluationResult on success.

    - min_score:      minimum NARI score (0-100)
    - certification:  minimum certification ("PASS" | "WARN" | "FAIL")
    - min_safety:     minimum safety metric score (0-1)
    - max_failures:   {metric_name: min_score} per-metric floors (0-1)
    """
    result = evaluate_trace(trace, case, judge=judge)
    problems: list[str] = []

    if min_score is not None and result.ninja_score < min_score:
        problems.append(f"score {result.ninja_score:.1f} < required {min_score}")

    if certification is not None:
        have = _CERT_RANK.get(result.certification, 0)
        need = _CERT_RANK.get(certification.upper(), 0)
        if have < need:
            problems.append(f"certification {result.certification} < required {certification.upper()}")

    if min_safety is not None:
        safety = result.metric_by_name("safety")
        s = safety.score if safety and safety.is_applicable else 1.0
        if s < min_safety:
            problems.append(f"safety {s:.2f} < required {min_safety}")

    for name, floor in (max_failures or {}).items():
        m = result.metric_by_name(name)
        if m is not None and m.is_applicable and m.score < floor:
            problems.append(f"{name} {m.score:.2f} < required {floor}")

    if problems:
        reasons = "; ".join(result.top_failure_reasons[:2])
        raise AssertionError(
            "Ninja Harness assertion failed: " + "; ".join(problems)
            + (f"  (top issues: {reasons})" if reasons else "")
        )
    return result
