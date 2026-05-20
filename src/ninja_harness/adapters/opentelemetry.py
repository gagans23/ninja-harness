"""
OpenTelemetry GenAI adapter.

Ingests traces that follow the OpenTelemetry GenAI semantic conventions
(`gen_ai.*` span attributes, `invoke_agent` / `execute_tool` operations).
Because most agent frameworks now emit OTel GenAI spans, this adapter offers a
truly framework-agnostic ingestion path.

Expected trace shape (simplified span list):

    {
      "_source": "opentelemetry",
      "spans": [
        {
          "name": "invoke_agent ResearchAgent",
          "attributes": {
            "gen_ai.operation.name": "invoke_agent",
            "gen_ai.agent.name": "ResearchAgent",
            "gen_ai.request.model": "gpt-4o",
            "gen_ai.input.messages": [{"role": "user", "content": "the task"}],
            "gen_ai.output.messages": [{"role": "assistant", "content": "answer"}],
            "gen_ai.usage.input_tokens": 100,
            "gen_ai.usage.output_tokens": 50
          },
          "status": {"code": "OK"}
        },
        {
          "name": "execute_tool web_search",
          "attributes": {
            "gen_ai.operation.name": "execute_tool",
            "gen_ai.tool.name": "web_search",
            "gen_ai.tool.call.arguments": {"query": "..."},
            "gen_ai.tool.call.result": "..."
          },
          "status": {"code": "OK"}
        }
      ]
    }

Reference:
- https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/
- https://opentelemetry.io/docs/specs/semconv/gen-ai/
"""

from __future__ import annotations

from typing import Any

from ninja_harness.adapters.base import TraceAdapter
from ninja_harness.schemas import AgentRun, AgentStep, ToolCall


def _gen_ai_attr_keys(span: dict) -> bool:
    attrs = span.get("attributes", {})
    return any(str(k).startswith("gen_ai.") for k in attrs)


def _extract_message_text(messages: Any) -> str:
    """Pull text out of a gen_ai messages attribute (list or string)."""
    if isinstance(messages, str):
        return messages
    if isinstance(messages, list) and messages:
        last = messages[-1]
        if isinstance(last, dict):
            content = last.get("content")
            if isinstance(content, list):  # parts form
                texts = [p.get("content", p.get("text", "")) for p in content if isinstance(p, dict)]
                return " ".join(t for t in texts if t)
            return str(content) if content is not None else ""
        return str(last)
    return ""


def _first_user_text(messages: Any) -> str:
    if isinstance(messages, list):
        for m in messages:
            if isinstance(m, dict) and m.get("role") == "user":
                content = m.get("content")
                return str(content) if content is not None else ""
    return _extract_message_text(messages)


class OpenTelemetryAdapter(TraceAdapter):
    """Parses OpenTelemetry GenAI span traces into an AgentRun."""

    def can_parse(self, raw: dict) -> bool:
        if raw.get("_source") == "opentelemetry":
            return True
        spans = raw.get("spans")
        if isinstance(spans, list) and spans:
            return any(_gen_ai_attr_keys(s) for s in spans)
        return False

    def parse(self, raw: dict) -> AgentRun:
        spans = raw.get("spans", [])
        if not spans:
            raise ValueError("OpenTelemetry trace has no spans to parse.")

        agent_name = raw.get("agent_name", "OTelAgent")
        task = raw.get("task", "")
        final_output = raw.get("final_output", "")

        steps: list[AgentStep] = []
        tool_calls: list[ToolCall] = []
        input_tokens = 0
        output_tokens = 0
        model: str | None = None

        for span in spans:
            attrs = span.get("attributes", {})
            op = attrs.get("gen_ai.operation.name", "")
            status_code = str(span.get("status", {}).get("code", "OK")).upper()
            step_status = "failed" if status_code in ("ERROR", "STATUS_CODE_ERROR") else "completed"

            input_tokens += int(attrs.get("gen_ai.usage.input_tokens", 0) or 0)
            output_tokens += int(attrs.get("gen_ai.usage.output_tokens", 0) or 0)
            if not model and attrs.get("gen_ai.request.model"):
                model = attrs.get("gen_ai.request.model")

            if op == "invoke_agent":
                name = attrs.get("gen_ai.agent.name", agent_name)
                if agent_name == "OTelAgent":
                    agent_name = name
                if not task:
                    task = _first_user_text(attrs.get("gen_ai.input.messages", ""))
                out_text = _extract_message_text(attrs.get("gen_ai.output.messages", ""))
                if out_text:
                    final_output = out_text
                steps.append(
                    AgentStep(
                        agent_name=name,
                        step_type="action",
                        output=out_text or None,
                        status=step_status,
                    )
                )
            elif op == "execute_tool":
                tool_name = attrs.get("gen_ai.tool.name", "unknown_tool")
                arguments = attrs.get("gen_ai.tool.call.arguments", {})
                if not isinstance(arguments, dict):
                    arguments = {"_raw": arguments}
                result = attrs.get("gen_ai.tool.call.result", attrs.get("gen_ai.tool.message"))
                tool_calls.append(
                    ToolCall(
                        tool_name=tool_name,
                        arguments=arguments,
                        result=str(result) if result is not None else None,
                        status="failed" if step_status == "failed" else "success",
                    )
                )
                steps.append(
                    AgentStep(
                        agent_name=agent_name,
                        step_type="observation",
                        output=str(result) if result is not None else None,
                        status=step_status,
                    )
                )
            else:
                # chat / other GenAI spans → generic action step
                out_text = _extract_message_text(attrs.get("gen_ai.output.messages", ""))
                steps.append(
                    AgentStep(
                        agent_name=agent_name,
                        step_type="action",
                        output=out_text or span.get("name"),
                        status=step_status,
                    )
                )

        if not final_output:
            raise ValueError(
                "OpenTelemetry trace produced no final output. Provide a top-level "
                "'final_output' or an invoke_agent span with gen_ai.output.messages."
            )

        token_usage = None
        if input_tokens or output_tokens:
            token_usage = {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            }

        metadata: dict[str, Any] = {"adapter": "opentelemetry"}
        if model:
            metadata["model"] = model

        return AgentRun(
            agent_name=agent_name,
            task=task,
            final_output=final_output,
            steps=steps,
            tool_calls=tool_calls,
            token_usage=token_usage,
            metadata=metadata,
        )
