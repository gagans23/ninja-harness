"""Tests for the judge calibration loop."""

from __future__ import annotations

import pytest

from ninja_harness.calibration import calibrate, calibrate_from_results
from ninja_harness.schemas import EvaluationResult, HumanLabel, MetricResult


def test_perfect_agreement() -> None:
    report = calibrate([(0.9, 0.9), (0.5, 0.5), (0.2, 0.2)])
    assert report.mean_abs_error == 0.0
    assert report.agreement_within_tolerance == 1.0
    assert report.pearson == pytest.approx(1.0)


def test_correlation_detects_linear_relationship() -> None:
    report = calibrate([(0.1, 0.2), (0.4, 0.5), (0.7, 0.8), (0.9, 1.0)])
    assert report.pearson is not None and report.pearson > 0.9


def test_spearman_handles_monotonic() -> None:
    report = calibrate([(0.1, 0.0), (0.2, 0.3), (0.3, 0.9)])
    assert report.spearman == pytest.approx(1.0)


def test_cohen_kappa_binary() -> None:
    # judge and human agree on pass/fail at 0.5 threshold for all
    report = calibrate([(0.9, 0.8), (0.2, 0.1), (0.6, 0.7), (0.3, 0.4)])
    assert report.cohen_kappa == pytest.approx(1.0)


def test_mae_and_tolerance() -> None:
    report = calibrate([(0.5, 0.7), (0.5, 0.5)], tolerance=0.1)
    assert report.mean_abs_error == pytest.approx(0.1)
    assert report.agreement_within_tolerance == 0.5  # one within, one not


def test_empty_raises() -> None:
    with pytest.raises(ValueError):
        calibrate([])


def test_small_sample_note() -> None:
    report = calibrate([(0.5, 0.5)])
    assert any("Small sample" in n for n in report.notes)


def test_calibrate_from_results_matches_by_run_id() -> None:
    results = [
        EvaluationResult(
            run_id="r1", ninja_score=80, grade="B", certification="PASS",
            metric_results=[MetricResult(name="goal_success", score=0.8, passed=True)],
        ),
        EvaluationResult(
            run_id="r2", ninja_score=40, grade="F", certification="FAIL",
            metric_results=[MetricResult(name="goal_success", score=0.3, passed=False)],
        ),
    ]
    labels = [
        HumanLabel(run_id="r1", metric="goal_success", human_score=0.75),
        HumanLabel(run_id="r2", metric="goal_success", human_score=0.35),
    ]
    report = calibrate_from_results(results, labels, metric="goal_success")
    assert report.n == 2
    assert report.metric == "goal_success"


def test_calibrate_from_results_no_match_raises() -> None:
    results = [EvaluationResult(run_id="r1", ninja_score=80, grade="B", certification="PASS")]
    labels = [HumanLabel(run_id="other", metric="goal_success", human_score=0.5)]
    with pytest.raises(ValueError):
        calibrate_from_results(results, labels, metric="goal_success")
