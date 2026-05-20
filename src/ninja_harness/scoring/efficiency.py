"""Efficiency Score — evaluates agent resource usage and execution discipline."""

from __future__ import annotations

from collections import Counter
from typing import Optional

from ninja_harness.schemas import AgentRun, EvaluationCase, MetricResult
from ninja_harness.scoring.base import BaseScorer

_PASS_THRESHOLD = 0.6

# Soft limits used when no case constraints are provided
_DEFAULT_MAX_STEPS = 20
_DEFAULT_MAX_TOOL_CALLS = 15
_DEFAULT_MAX_LATENCY_SECONDS = 60.0


class EfficiencyScorer(BaseScorer):
    """
    Measures how efficiently the agent executed the task.

    Penalises:
    - Exceeding max_steps / max_tool_calls / max_latency from the eval case
    - Repeated identical tool calls (looping behavior)
    - Excessive total tool calls relative to soft default limits
    """

    @property
    def name(self) -> str:
        return "efficiency"

    def score(
        self,
        run: AgentRun,
        case: Optional[EvaluationCase] = None,
    ) -> MetricResult:
        max_steps = (case.max_steps if case and case.max_steps else _DEFAULT_MAX_STEPS)
        max_tool_calls = (
            case.max_tool_calls if case and case.max_tool_calls else _DEFAULT_MAX_TOOL_CALLS
        )
        max_latency = (
            case.max_latency_seconds
            if case and case.max_latency_seconds
            else _DEFAULT_MAX_LATENCY_SECONDS
        )

        step_count = len(run.steps)
        tool_count = len(run.tool_calls)
        latency = run.latency_seconds

        failures: list[str] = []
        recommendations: list[str] = []
        penalty = 0.0

        # Step count penalty
        if step_count > max_steps:
            overage = (step_count - max_steps) / max_steps
            penalty += min(0.3, overage * 0.3)
            failures.append(
                f"Step count {step_count} exceeds limit {max_steps} "
                f"(+{step_count - max_steps} over)"
            )
            recommendations.append(
                "Review whether the agent plan can be condensed or redundant steps removed."
            )

        # Tool call count penalty
        if tool_count > max_tool_calls:
            overage = (tool_count - max_tool_calls) / max_tool_calls
            penalty += min(0.3, overage * 0.3)
            failures.append(
                f"Tool call count {tool_count} exceeds limit {max_tool_calls} "
                f"(+{tool_count - max_tool_calls} over)"
            )
            recommendations.append(
                "Consider batching or reducing redundant tool invocations."
            )

        # Repeated tool calls (same name + args)
        tool_keys = [
            f"{tc.tool_name}::{sorted(tc.arguments.items())}" for tc in run.tool_calls
        ]
        key_counts = Counter(tool_keys)
        duplicates = {k: v for k, v in key_counts.items() if v > 1}
        if duplicates:
            dup_penalty = min(0.2, len(duplicates) * 0.05)
            penalty += dup_penalty
            dup_names = [k.split("::")[0] for k in list(duplicates.keys())[:3]]
            failures.append(
                f"Detected {len(duplicates)} repeated tool call(s): {', '.join(dup_names)}"
            )
            recommendations.append(
                "Repeated identical tool calls suggest looping or missing state tracking. "
                "Add deduplication or caching logic to the agent."
            )

        # Latency penalty
        if latency is not None and latency > max_latency:
            overage = (latency - max_latency) / max_latency
            penalty += min(0.2, overage * 0.2)
            failures.append(
                f"Latency {latency:.1f}s exceeds limit {max_latency:.1f}s"
            )
            recommendations.append(
                "Profile tool call latency and consider parallelising independent calls."
            )

        score = max(0.0, 1.0 - penalty)
        passed = score >= _PASS_THRESHOLD

        details: dict = {
            "step_count": step_count,
            "tool_call_count": tool_count,
            "duplicate_tool_calls": len(duplicates),
            "latency_seconds": latency,
            "max_steps_limit": max_steps,
            "max_tool_calls_limit": max_tool_calls,
            "max_latency_limit": max_latency,
        }
        if run.token_usage:
            details["token_usage"] = run.token_usage
        if run.cost is not None:
            details["cost"] = run.cost

        return MetricResult(
            name=self.name,
            score=round(score, 4),
            passed=passed,
            details=details,
            failure_reasons=failures,
            recommendations=recommendations,
        )
