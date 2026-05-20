"""
AutoGen adapter.

Parses Microsoft AutoGen conversation traces (AssistantAgent, UserProxyAgent,
GroupChatManager) into an AgentRun.

Expected trace shape:

    {
      "_source": "autogen",
      "task": "the initial request",
      "chat_history": [
        {"name": "user_proxy", "role": "user", "content": "the task"},
        {"name": "assistant", "role": "assistant", "content": "...",
         "tool_calls": [
           {"function": {"name": "calculator", "arguments": {"expr": "2+2"}}}
         ]},
        {"name": "user_proxy", "role": "tool", "content": "4",
         "tool_name": "calculator"},
        {"name": "assistant", "role": "assistant", "content": "The answer is 4."}
      ]
    }

Notes:
- Each chat message maps to an AgentStep.
- function/tool calls in messages map to ToolCall.
- Messages flowing between distinct agent names map to Handoff (group chat).

Reference: https://microsoft.github.io/autogen/
"""

from __future__ import annotations

import json
from typing import Any

from ninja_harness.adapters.base import TraceAdapter
from ninja_harness.schemas import AgentRun, AgentStep, Handoff, ToolCall


class AutoGenAdapter(TraceAdapter):
    """Parses AutoGen conversation traces into an AgentRun."""

    def can_parse(self, raw: dict) -> bool:
        if raw.get("_source") == "autogen":
            return True
        return "chat_history" in raw and isinstance(raw.get("chat_history"), list)

    def parse(self, raw: dict) -> AgentRun:
        history = raw.get("chat_history", [])
        if not history:
            raise ValueError("AutoGen trace has no chat_history to parse.")

        task = raw.get("task") or self._first_user_content(history)

        steps: list[AgentStep] = []
        tool_calls: list[ToolCall] = []
        handoffs: list[Handoff] = []

        final_output = ""
        last_assistant_name: str | None = None
        last_assistant_content = ""

        for msg in history:
            name = msg.get("name", "agent")
            role = msg.get("role", "assistant")
            content = msg.get("content") or ""

            if role == "tool" or msg.get("tool_responses"):
                tool_name = msg.get("tool_name", "unknown_tool")
                for tc in reversed(tool_calls):
                    if tc.tool_name == tool_name and tc.result is None:
                        tc.result = str(content)
                        break
                steps.append(
                    AgentStep(
                        agent_name=name,
                        step_type="observation",
                        output=str(content),
                        status="completed",
                    )
                )
                continue

            if role == "user":
                steps.append(
                    AgentStep(
                        agent_name=name,
                        step_type="plan",
                        input=content,
                        status="completed",
                    )
                )
                continue

            # assistant message
            if content:
                final_output = content

            if last_assistant_name is not None and name != last_assistant_name:
                handoffs.append(
                    Handoff(
                        source_agent=last_assistant_name,
                        target_agent=name,
                        reason=msg.get("handoff_reason", "AutoGen agent turn transfer"),
                        context_summary=last_assistant_content[:200],
                        expected_next_action=content[:200],
                        task_id=raw.get("task_id"),
                        trace_id=raw.get("trace_id"),
                    )
                )
                steps.append(
                    AgentStep(
                        agent_name=last_assistant_name,
                        step_type="handoff",
                        output=f"Turn passed to {name}",
                        status="completed",
                    )
                )

            steps.append(
                AgentStep(
                    agent_name=name,
                    step_type="action",
                    output=content,
                    status="completed",
                )
            )

            for tc in msg.get("tool_calls", []):
                fn = tc.get("function", tc)
                tool_calls.append(
                    ToolCall(
                        tool_name=fn.get("name", "unknown_tool"),
                        arguments=self._parse_arguments(fn.get("arguments", {})),
                        status="success",
                    )
                )

            last_assistant_name = name
            last_assistant_content = content

        agent_name = raw.get("agent_name") or last_assistant_name or "AutoGenAgent"

        return AgentRun(
            agent_name=agent_name,
            task=task,
            final_output=final_output,
            steps=steps,
            tool_calls=tool_calls,
            handoffs=handoffs,
            metadata={"adapter": "autogen"},
        )

    def _first_user_content(self, history: list[dict]) -> str:
        for m in history:
            if m.get("role") == "user":
                return str(m.get("content", ""))
        return str(history[0].get("content", "")) if history else ""

    def _parse_arguments(self, args: Any) -> dict:
        if isinstance(args, dict):
            return args
        if isinstance(args, str):
            try:
                parsed = json.loads(args)
                return parsed if isinstance(parsed, dict) else {"_raw": args}
            except json.JSONDecodeError:
                return {"_raw": args}
        return {}
