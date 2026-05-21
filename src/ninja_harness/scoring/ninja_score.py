"""Ninja Agent Reliability Index (NARI) — composite score aggregator."""

from __future__ import annotations

from ninja_harness.certification import compute_certification, compute_grade
from ninja_harness.schemas import (
    AgentRun,
    EvaluationCase,
    EvaluationResult,
    MetricResult,
)
from ninja_harness.scoring.efficiency import EfficiencyScorer
from ninja_harness.scoring.goal_success import GoalSuccessScorer
from ninja_harness.scoring.grounding import GroundingScorer
from ninja_harness.scoring.handoff_integrity import HandoffIntegrityScorer
from ninja_harness.scoring.judge import Judge
from ninja_harness.scoring.output_hygiene import OutputHygieneScorer
from ninja_harness.scoring.recovery import RecoveryScorer
from ninja_harness.scoring.safety import SafetyScorer
from ninja_harness.scoring.stability import StabilityScorer
from ninja_harness.scoring.tool_call_f1 import ToolCallF1Scorer

# Weights must sum to 1.0
_WEIGHTS: dict[str, float] = {
    "goal_success": 0.25,
    "tool_call_f1": 0.15,
    "handoff_integrity": 0.15,
    "grounding": 0.15,
    "safety": 0.10,
    "efficiency": 0.10,
    "recovery": 0.05,
    "stability": 0.05,
}

assert abs(sum(_WEIGHTS.values()) - 1.0) < 1e-9, "NARI weights must sum to 1.0"


class NinjaScoreAggregator:
    """
    Runs all scorers and produces the composite Ninja Agent Reliability Index.

    Metrics marked not-applicable (score == -1.0) are excluded from the
    weighted average; their weight is redistributed proportionally among
    applicable metrics.
    """

    def __init__(
        self,
        baseline_path: str | None = None,
        judge: Judge | None = None,
    ) -> None:
        self._scorers = [
            GoalSuccessScorer(judge=judge),
            ToolCallF1Scorer(),
            HandoffIntegrityScorer(),
            GroundingScorer(),
            SafetyScorer(),
            EfficiencyScorer(),
            RecoveryScorer(),
            StabilityScorer(baseline_path=baseline_path),
            # Reported separately — not part of the weighted composite (weight 0).
            OutputHygieneScorer(),
        ]

    def evaluate(
        self,
        run: AgentRun,
        case: EvaluationCase | None = None,
    ) -> EvaluationResult:
        metric_results: list[MetricResult] = []
        for scorer in self._scorers:
            result = scorer.score(run, case)
            metric_results.append(result)

        ninja_score = self._compute_composite(metric_results)

        # Inject current scores into run metadata for stability scorer (if re-run)
        safety_result = next(
            (m for m in metric_results if m.name == "safety"), None
        )
        safety_score = safety_result.score if safety_result and safety_result.is_applicable else 1.0

        grade = compute_grade(ninja_score)
        certification = compute_certification(ninja_score, safety_score)

        # Aggregate failure reasons and recommendations
        all_failures: list[str] = []
        all_recommendations: list[str] = []
        for mr in metric_results:
            all_failures.extend(mr.failure_reasons)
            all_recommendations.extend(mr.recommendations)

        top_failures = all_failures[:3]
        top_recommendations = list(dict.fromkeys(all_recommendations))[:5]

        return EvaluationResult(
            run_id=run.run_id,
            case_id=case.case_id if case else None,
            metric_results=metric_results,
            ninja_score=ninja_score,
            grade=grade,
            certification=certification,
            top_failure_reasons=top_failures,
            recommended_fixes=top_recommendations,
        )

    def _compute_composite(self, results: list[MetricResult]) -> float:
        applicable = [r for r in results if r.is_applicable]
        if not applicable:
            return 0.0

        applicable_weight_total = sum(
            _WEIGHTS.get(r.name, 0.0) for r in applicable
        )
        if applicable_weight_total == 0:
            return 0.0

        weighted_sum = 0.0
        for r in applicable:
            weight = _WEIGHTS.get(r.name, 0.0)
            normalized_weight = weight / applicable_weight_total
            weighted_sum += normalized_weight * r.score

        return round(weighted_sum * 100, 2)
