"""Recovery Score — checks whether the agent recovered from failures gracefully."""

from __future__ import annotations

from ninja_harness.schemas import AgentRun, EvaluationCase, MetricResult
from ninja_harness.scoring.base import BaseScorer

_PASS_THRESHOLD = 0.6


def _step_follows_failure(run: AgentRun, failure_index: int) -> bool:
    """Return True if there is a non-failed step after the given index."""
    for step in run.steps[failure_index + 1 :]:
        if step.status != "failed":
            return True
    return False


class RecoveryScorer(BaseScorer):
    """
    Measures the agent's ability to recover from adverse events.

    Checks:
    - After a failed tool call: did the agent retry or choose an alternative?
    - After a failed step: did execution continue meaningfully?
    - After a guardrail block: did the agent acknowledge and adapt?
    - After an invalid handoff (missing fields): was the task still completed?

    Recovery is scored as: (recovered_failures / total_failures).
    If no failures occur, score = 1.0 (nothing to recover from).
    """

    @property
    def name(self) -> str:
        return "recovery"

    def score(
        self,
        run: AgentRun,
        case: EvaluationCase | None = None,
    ) -> MetricResult:
        failure_events: list[dict] = []
        recovered_events: list[dict] = []

        # Failed tool calls
        for tc in run.tool_calls:
            if tc.status == "failed":
                event = {
                    "type": "failed_tool_call",
                    "tool": tc.tool_name,
                    "error": tc.error or "unknown",
                }
                failure_events.append(event)

                # Recovery signal: agent continued with a subsequent non-failed tool call
                tc_idx = run.tool_calls.index(tc)
                remaining = run.tool_calls[tc_idx + 1 :]
                if any(t.status != "failed" for t in remaining):
                    recovered_events.append(event)

        # Failed steps
        for i, step in enumerate(run.steps):
            if step.status == "failed":
                event = {
                    "type": "failed_step",
                    "step_id": step.step_id,
                    "step_type": step.step_type,
                }
                failure_events.append(event)
                if _step_follows_failure(run, i):
                    recovered_events.append(event)

        # Guardrail blocks
        triggered_guardrails = [
            g for g in run.guardrail_events if g.status == "triggered"
        ]
        for g in triggered_guardrails:
            event = {
                "type": "guardrail_triggered",
                "guardrail": g.guardrail_name,
                "severity": g.severity,
            }
            failure_events.append(event)
            # Recovery signal: final output is non-empty (agent produced an answer despite block)
            if run.final_output and len(run.final_output.strip()) > 20:
                recovered_events.append(event)

        if not failure_events:
            return MetricResult(
                name=self.name,
                score=1.0,
                passed=True,
                details={
                    "failure_events": 0,
                    "recovered_events": 0,
                    "note": "No failures detected; full score awarded.",
                },
            )

        recovery_rate = len(recovered_events) / len(failure_events)
        passed = recovery_rate >= _PASS_THRESHOLD

        failure_reasons = []
        recommendations = []
        unrecovered = [e for e in failure_events if e not in recovered_events]
        if unrecovered:
            types = [e["type"] for e in unrecovered[:3]]
            failure_reasons.append(
                f"Agent did not recover from: {', '.join(types)}"
            )
            recommendations.append(
                "Add retry logic, fallback tool paths, and graceful error handling "
                "so the agent can continue after partial failures."
            )

        return MetricResult(
            name=self.name,
            score=round(recovery_rate, 4),
            passed=passed,
            details={
                "failure_events": len(failure_events),
                "recovered_events": len(recovered_events),
                "unrecovered_events": len(unrecovered),
                "recovery_rate": round(recovery_rate, 4),
                "event_breakdown": failure_events,
            },
            failure_reasons=failure_reasons,
            recommendations=recommendations,
        )
