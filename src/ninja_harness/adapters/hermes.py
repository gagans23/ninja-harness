"""
Hermes multi-agent adapter.

Parses Hermes-style traces — OpenAI-style message arrays with role/content
and function/tool calls, optionally annotated with agent names for
multi-agent delegation.

Expected trace shape:

    {
      "_source": "hermes",
      "agent_name": "OrchestratorAgent",
      "task": "optional explicit task (else taken from first user message)",
      "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "the task"},
        {"role": "assistant", "agent": "OrchestratorAgent",
         "content": "thinking...",
         "tool_calls": [
           {"function": {"name": "web_search",
                         "arguments": "{\"query\": \"...\"}"}}
         ]},
        {"role": "tool", "name": "web_search", "content": "result"},
        {"role": "assistant", "agent": "OrchestratorAgent",
         "content": "final answer"}
      ]
    }

Multi-agent handoff: when consecutive assistant messages carry different
"agent" names, a Handoff is inferred between them.

Reference: Hermes function-calling prompt format (message-array based).
"""

from __future__ import annotations

import json
from typing import Any

from ninja_harness.adapters.base import TraceAdapter
from ninja_harness.schemas import AgentRun, AgentStep, Handoff, ToolCall


class HermesAdapter(TraceAdapter):
    """Parses Hermes-style message-array multi-agent traces into an AgentRun."""

    def can_parse(self, raw: dict) -> bool:
        if raw.get("_source") == "hermes":
            return True
        messages = raw.get("messages")
        if not isinstance(messages, list):
            return False
        has_tool = any(m.get("role") == "tool" for m in messages)
        has_tool_calls = any("tool_calls" in m for m in messages)
        return has_tool or has_tool_calls

    def parse(self, raw: dict) -> AgentRun:
        messages = raw.get("messages", [])
        if not messages:
            raise ValueError("Hermes trace has no messages to parse.")

        default_agent = raw.get("agent_name", "HermesAgent")
        task = raw.get("task") or self._first_user_message(messages)

        steps: list[AgentStep] = []
        tool_calls: list[ToolCall] = []
        handoffs: list[Handoff] = []

        last_assistant_agent: str | None = None
        last_assistant_content: str = ""
        final_output = ""
        pending_tool_names: list[str] = []

        for msg in messages:
            role = msg.get("role")
            agent = msg.get("agent", default_agent)

            if role == "assistant":
                content = msg.get("content") or ""
                if content:
                    final_output = content
                    last_assistant_content = content

                # Detect multi-agent handoff
                if (
                    last_assistant_agent is not None
                    and agent != last_assistant_agent
                ):
                    handoffs.append(
                        Handoff(
                            source_agent=last_assistant_agent,
                            target_agent=agent,
                            reason=msg.get("handoff_reason", "Multi-agent delegation"),
                            context_summary=last_assistant_content[:200],
                            expected_next_action=content[:200] if content else "",
                            task_id=raw.get("task_id"),
                            trace_id=raw.get("trace_id"),
                        )
                    )
                    steps.append(
                        AgentStep(
                            agent_name=last_assistant_agent,
                            step_type="handoff",
                            output=f"Handoff to {agent}",
                            status="completed",
                        )
                    )

                steps.append(
                    AgentStep(
                        agent_name=agent,
                        step_type="action",
                        output=content,
                        status="completed",
                    )
                )

                for tc in msg.get("tool_calls", []):
                    fn = tc.get("function", tc)
                    name = fn.get("name", "unknown_tool")
                    pending_tool_names.append(name)
                    tool_calls.append(
                        ToolCall(
                            tool_name=name,
                            arguments=self._parse_arguments(fn.get("arguments", {})),
                            status="success",
                        )
                    )

                last_assistant_agent = agent

            elif role == "tool":
                tool_name = msg.get("name", "unknown_tool")
                result = msg.get("content", "")
                # Attach result to the matching pending tool call
                for tc in reversed(tool_calls):
                    if tc.tool_name == tool_name and tc.result is None:
                        tc.result = str(result)
                        break
                steps.append(
                    AgentStep(
                        agent_name=last_assistant_agent or default_agent,
                        step_type="observation",
                        output=str(result),
                        status="completed",
                    )
                )

            elif role == "user":
                steps.append(
                    AgentStep(
                        agent_name="user",
                        step_type="plan",
                        input=msg.get("content", ""),
                        status="completed",
                    )
                )

        return AgentRun(
            agent_name=default_agent,
            task=task,
            final_output=final_output,
            steps=steps,
            tool_calls=tool_calls,
            handoffs=handoffs,
            metadata={"adapter": "hermes"},
        )

    def _first_user_message(self, messages: list[dict]) -> str:
        for m in messages:
            if m.get("role") == "user":
                return str(m.get("content", ""))
        return ""

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
