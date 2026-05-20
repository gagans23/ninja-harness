"""CustomJsonAdapter — full implementation for Ninja Harness native JSON traces."""

from __future__ import annotations

from ninja_harness.adapters.base import TraceAdapter
from ninja_harness.schemas import (
    AgentRun,
    AgentStep,
    GuardrailEvent,
    Handoff,
    ToolCall,
)


class CustomJsonAdapter(TraceAdapter):
    """
    Parses traces that directly match the Ninja Harness AgentRun JSON schema.

    This is the reference format. All other adapters translate their
    framework-native fields into this shape.

    Required top-level fields: agent_name, task, final_output.
    All other fields are optional and will be defaulted.
    """

    def can_parse(self, raw: dict) -> bool:
        required = {"agent_name", "task", "final_output"}
        return required.issubset(raw.keys())

    def parse(self, raw: dict) -> AgentRun:
        steps = [self._parse_step(s) for s in raw.get("steps", [])]
        tool_calls = [self._parse_tool_call(tc) for tc in raw.get("tool_calls", [])]
        handoffs = [self._parse_handoff(h) for h in raw.get("handoffs", [])]
        guardrail_events = [
            self._parse_guardrail(g) for g in raw.get("guardrail_events", [])
        ]

        extra: dict = {}
        if run_id := raw.get("run_id"):
            extra["run_id"] = run_id

        return AgentRun(
            **extra,
            agent_name=raw["agent_name"],
            task=raw["task"],
            final_output=raw["final_output"],
            expected_output=raw.get("expected_output"),
            steps=steps,
            tool_calls=tool_calls,
            handoffs=handoffs,
            guardrail_events=guardrail_events,
            start_time=raw.get("start_time"),
            end_time=raw.get("end_time"),
            token_usage=raw.get("token_usage"),
            cost=raw.get("cost"),
            metadata=raw.get("metadata", {}),
        )

    def _parse_step(self, raw: dict) -> AgentStep:
        return AgentStep(
            step_id=raw.get("step_id", ""),
            agent_name=raw.get("agent_name", "unknown"),
            step_type=raw.get("step_type", "action"),
            input=raw.get("input"),
            output=raw.get("output"),
            status=raw.get("status", "completed"),
            error=raw.get("error"),
            metadata=raw.get("metadata", {}),
        )

    def _parse_tool_call(self, raw: dict) -> ToolCall:
        return ToolCall(
            tool_name=raw.get("tool_name", "unknown"),
            arguments=raw.get("arguments", {}),
            result=raw.get("result"),
            status=raw.get("status", "unknown"),
            error=raw.get("error"),
            timestamp=raw.get("timestamp"),
        )

    def _parse_handoff(self, raw: dict) -> Handoff:
        return Handoff(
            source_agent=raw.get("source_agent", ""),
            target_agent=raw.get("target_agent", ""),
            reason=raw.get("reason", ""),
            context_summary=raw.get("context_summary", ""),
            expected_next_action=raw.get("expected_next_action", ""),
            task_id=raw.get("task_id"),
            trace_id=raw.get("trace_id"),
            metadata=raw.get("metadata", {}),
        )

    def _parse_guardrail(self, raw: dict) -> GuardrailEvent:
        return GuardrailEvent(
            guardrail_name=raw.get("guardrail_name", "unknown"),
            status=raw.get("status", "passed"),
            message=raw.get("message", ""),
            severity=raw.get("severity", "low"),
            metadata=raw.get("metadata", {}),
        )
