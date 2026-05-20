"""Handoff Integrity Score — checks completeness of agent-to-agent handoffs."""

from __future__ import annotations

from typing import Optional

from ninja_harness.schemas import AgentRun, EvaluationCase, Handoff, MetricResult
from ninja_harness.scoring.base import BaseScorer

_PASS_THRESHOLD = 0.75

# Required fields and their weights (must sum to 1.0)
_FIELD_WEIGHTS: dict[str, float] = {
    "source_agent": 0.20,
    "target_agent": 0.20,
    "reason": 0.20,
    "context_summary": 0.20,
    "expected_next_action": 0.15,
    "task_id_or_trace_id": 0.05,
}


def _score_handoff(h: Handoff) -> tuple[float, list[str]]:
    """Return (0–1 score, list of missing field names) for a single handoff."""
    missing: list[str] = []
    score = 0.0

    if h.source_agent.strip():
        score += _FIELD_WEIGHTS["source_agent"]
    else:
        missing.append("source_agent")

    if h.target_agent.strip():
        score += _FIELD_WEIGHTS["target_agent"]
    else:
        missing.append("target_agent")

    if h.reason.strip():
        score += _FIELD_WEIGHTS["reason"]
    else:
        missing.append("reason")

    if h.context_summary.strip():
        score += _FIELD_WEIGHTS["context_summary"]
    else:
        missing.append("context_summary")

    if h.expected_next_action.strip():
        score += _FIELD_WEIGHTS["expected_next_action"]
    else:
        missing.append("expected_next_action")

    if h.task_id or h.trace_id:
        score += _FIELD_WEIGHTS["task_id_or_trace_id"]
    else:
        missing.append("task_id or trace_id")

    return round(score, 4), missing


class HandoffIntegrityScorer(BaseScorer):
    """
    Measures how completely each agent-to-agent handoff is documented.

    A handoff with missing context, reason, or linkage IDs can cause
    downstream agents to proceed without adequate context — a common
    source of multi-agent failures in production.
    """

    @property
    def name(self) -> str:
        return "handoff_integrity"

    def score(
        self,
        run: AgentRun,
        case: Optional[EvaluationCase] = None,
    ) -> MetricResult:
        if not run.handoffs:
            return self._not_applicable("No handoffs in this run; metric not applicable.")

        per_handoff: list[dict] = []
        all_missing: list[str] = []

        for i, h in enumerate(run.handoffs):
            hs, missing = _score_handoff(h)
            per_handoff.append(
                {
                    "index": i,
                    "source": h.source_agent,
                    "target": h.target_agent,
                    "score": hs,
                    "missing_fields": missing,
                }
            )
            if missing:
                all_missing.extend(
                    [f"Handoff {i} ({h.source_agent}→{h.target_agent}): missing {', '.join(missing)}"]
                )

        avg_score = sum(p["score"] for p in per_handoff) / len(per_handoff)
        passed = avg_score >= _PASS_THRESHOLD

        failure_reasons = all_missing[:5] if all_missing else []
        recommendations = []
        if not passed:
            recommendations.append(
                "Ensure every handoff includes source_agent, target_agent, reason, "
                "context_summary, expected_next_action, and either task_id or trace_id."
            )

        return MetricResult(
            name=self.name,
            score=round(avg_score, 4),
            passed=passed,
            details={
                "handoff_count": len(run.handoffs),
                "per_handoff_scores": per_handoff,
                "average_score": round(avg_score, 4),
            },
            failure_reasons=failure_reasons,
            recommendations=recommendations,
        )
