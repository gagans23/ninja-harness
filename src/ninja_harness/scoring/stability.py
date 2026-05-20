"""Stability Score — regression detection vs a stored baseline evaluation."""

from __future__ import annotations

import json
from pathlib import Path

from ninja_harness.schemas import AgentRun, EvaluationCase, MetricResult
from ninja_harness.scoring.base import BaseScorer

_PASS_THRESHOLD = 0.8
_REGRESSION_THRESHOLD = 0.05  # >5% drop from baseline is flagged


class StabilityScorer(BaseScorer):
    """
    Compares the current run's metric scores against a stored baseline JSON.

    The baseline JSON is produced by saving a previous EvaluationResult.
    If no baseline is provided, the metric is marked not applicable.

    Usage:
        scorer = StabilityScorer(baseline_path="baselines/my_agent.json")
    """

    def __init__(self, baseline_path: str | None = None) -> None:
        self._baseline_path = baseline_path
        self._baseline: dict | None = None
        if baseline_path:
            path = Path(baseline_path)
            if path.exists():
                with path.open() as f:
                    self._baseline = json.load(f)

    @property
    def name(self) -> str:
        return "stability"

    def score(
        self,
        run: AgentRun,
        case: EvaluationCase | None = None,
    ) -> MetricResult:
        if not self._baseline:
            return self._not_applicable(
                "No baseline JSON provided; stability comparison not available. "
                "Pass --baseline to enable regression detection."
            )

        baseline_score = self._baseline.get("ninja_score")
        if baseline_score is None:
            return self._not_applicable(
                "Baseline JSON does not contain a 'ninja_score' field."
            )

        # Stability score = how much of the baseline score has been preserved.
        # We derive this lazily from the current run's ninja_score stored in metadata.
        current_score_raw = run.metadata.get("current_ninja_score")
        if current_score_raw is None:
            return self._not_applicable(
                "Current ninja_score not yet available in run metadata. "
                "Stability is computed after the full evaluation pipeline."
            )

        current_score = float(current_score_raw)
        delta = current_score - baseline_score

        if baseline_score > 0:
            retention = current_score / baseline_score
        else:
            retention = 1.0

        stability_score = min(1.0, max(0.0, retention))
        passed = stability_score >= _PASS_THRESHOLD

        failure_reasons = []
        recommendations = []
        if delta < -(_REGRESSION_THRESHOLD * baseline_score):
            failure_reasons.append(
                f"Score dropped {abs(delta):.1f} points from baseline "
                f"({baseline_score:.1f} → {current_score:.1f})"
            )
            recommendations.append(
                "Review recent changes to the agent that may have caused regression. "
                "Consider pinning the baseline and running A/B comparisons."
            )

        # Compare per-metric scores if available
        per_metric_delta = []
        baseline_metrics = {
            m["name"]: m["score"]
            for m in self._baseline.get("metric_results", [])
        }
        current_metrics = run.metadata.get("current_metric_scores", {})
        for metric_name, baseline_metric_score in baseline_metrics.items():
            curr = current_metrics.get(metric_name)
            if curr is not None and baseline_metric_score > 0:
                drop = baseline_metric_score - float(curr)
                if drop > _REGRESSION_THRESHOLD:
                    per_metric_delta.append(
                        {
                            "metric": metric_name,
                            "baseline": baseline_metric_score,
                            "current": float(curr),
                            "drop": round(drop, 4),
                        }
                    )

        return MetricResult(
            name=self.name,
            score=round(stability_score, 4),
            passed=passed,
            details={
                "baseline_ninja_score": baseline_score,
                "current_ninja_score": current_score,
                "delta": round(delta, 2),
                "retention_ratio": round(retention, 4),
                "metric_regressions": per_metric_delta,
            },
            failure_reasons=failure_reasons,
            recommendations=recommendations,
        )
