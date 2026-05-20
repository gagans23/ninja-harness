"""
OpenAI Agents SDK adapter.

Parses serialized run traces produced by the OpenAI Agents SDK
(openai-agents-python: Agent, Runner, handoff, function_tool).

Expected trace shape (a serialized RunResult):

    {
      "_source": "openai_agents_sdk",
      "agent": {"name": "TriageAgent"},
      "input": "the task / user request",
      "final_output": "the final answer",
      "new_items": [
        {"type": "message_output_item", "agent": "TriageAgent",
         "raw_item": {"content": "..."}},
        {"type": "tool_call_item", "agent": "TriageAgent",
         "raw_item": {"name": "web_search", "arguments": {"query": "..."}}},
        {"type": "tool_call_output_item", "agent": "TriageAgent",
         "output": "tool result text"},
        {"type": "handoff_call_item", "agent": "TriageAgent",
         "raw_item": {"name": "transfer_to_BillingAgent"}},
        {"type": "handoff_output_item", "source_agent": "TriageAgent",
         "target_agent": "BillingAgent"}
      ],
      "guardrail_results": [
        {"name": "input_pii_guard", "tripwire_triggered": false,
         "output_info": "..."}
      ],
      "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}
    }

Reference: https://openai.github.io/openai-agents-python/
"""

from __future__ import annotations

from typing import Any

from ninja_harness.adapters.base import TraceAdapter
from ninja_harness.schemas import (
    AgentRun,
    AgentStep,
    GuardrailEvent,
    Handoff,
    ToolCall,
)

_ITEM_STEP_TYPE = {
    "message_output_item": "action",
    "tool_call_item": "action",
    "tool_call_output_item": "observation",
    "handoff_call_item": "handoff",
    "handoff_output_item": "handoff",
    "reasoning_item": "plan",
}


class OpenAIAgentsAdapter(TraceAdapter):
    """Parses OpenAI Agents SDK serialized run traces into an AgentRun."""

    def can_parse(self, raw: dict) -> bool:
        if raw.get("_source") == "openai_agents_sdk":
            return True
        return "new_items" in raw and "agent" in raw and "final_output" in raw

    def parse(self, raw: dict) -> AgentRun:
        agent = raw.get("agent", {})
        agent_name = agent.get("name") if isinstance(agent, dict) else str(agent)
        if not agent_name:
            agent_name = raw.get("agent_name", "OpenAIAgent")

        if "final_output" not in raw:
            raise ValueError(
                "OpenAI Agents trace missing 'final_output'. "
                "Expected a serialized RunResult with a final_output field."
            )

        steps: list[AgentStep] = []
        tool_calls: list[ToolCall] = []
        handoffs: list[Handoff] = []

        pending_tool: dict[str, Any] | None = None

        for item in raw.get("new_items", []):
            item_type = item.get("type", "")
            item_agent = item.get("agent", agent_name)
            step_type = _ITEM_STEP_TYPE.get(item_type, "action")
            raw_item = item.get("raw_item", {})

            if item_type == "tool_call_item":
                pending_tool = {
                    "tool_name": raw_item.get("name", "unknown_tool"),
                    "arguments": self._coerce_args(raw_item.get("arguments", {})),
                }
                steps.append(
                    AgentStep(
                        agent_name=item_agent,
                        step_type="action",
                        output=f"Calling tool {pending_tool['tool_name']}",
                        status="completed",
                    )
                )
            elif item_type == "tool_call_output_item":
                result = item.get("output", raw_item.get("output"))
                tool_name = (
                    pending_tool["tool_name"] if pending_tool else raw_item.get("name", "unknown_tool")
                )
                arguments = pending_tool["arguments"] if pending_tool else {}
                tool_calls.append(
                    ToolCall(
                        tool_name=tool_name,
                        arguments=arguments,
                        result=str(result) if result is not None else None,
                        status="success",
                    )
                )
                pending_tool = None
                steps.append(
                    AgentStep(
                        agent_name=item_agent,
                        step_type="observation",
                        output=str(result) if result is not None else None,
                        status="completed",
                    )
                )
            elif item_type == "handoff_output_item":
                source = item.get("source_agent", agent_name)
                target = item.get("target_agent", "")
                handoffs.append(
                    Handoff(
                        source_agent=source,
                        target_agent=target,
                        reason=item.get("reason", f"Handoff from {source} to {target}"),
                        context_summary=item.get("context_summary", ""),
                        expected_next_action=item.get("expected_next_action", ""),
                        task_id=raw.get("task_id"),
                        trace_id=raw.get("trace_id"),
                    )
                )
                steps.append(
                    AgentStep(
                        agent_name=source,
                        step_type="handoff",
                        output=f"Handoff to {target}",
                        status="completed",
                    )
                )
            else:
                content = raw_item.get("content") if isinstance(raw_item, dict) else None
                steps.append(
                    AgentStep(
                        agent_name=item_agent,
                        step_type=step_type,
                        output=str(content) if content else None,
                        status="completed",
                    )
                )

        guardrail_events = [
            self._parse_guardrail(g) for g in raw.get("guardrail_results", [])
        ]

        token_usage = raw.get("usage")

        return AgentRun(
            agent_name=agent_name,
            task=str(raw.get("input", "")),
            final_output=str(raw["final_output"]),
            steps=steps,
            tool_calls=tool_calls,
            handoffs=handoffs,
            guardrail_events=guardrail_events,
            token_usage=token_usage,
            metadata={"adapter": "openai_agents_sdk"},
        )

    def _coerce_args(self, args: Any) -> dict:
        if isinstance(args, dict):
            return args
        if isinstance(args, str):
            import json

            try:
                parsed = json.loads(args)
                return parsed if isinstance(parsed, dict) else {"_raw": args}
            except json.JSONDecodeError:
                return {"_raw": args}
        return {}

    def _parse_guardrail(self, g: dict) -> GuardrailEvent:
        triggered = g.get("tripwire_triggered", False)
        return GuardrailEvent(
            guardrail_name=g.get("name", "guardrail"),
            status="triggered" if triggered else "passed",
            message=str(g.get("output_info", "")),
            severity="high" if triggered else "low",
        )
