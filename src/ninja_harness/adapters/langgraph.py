"""
LangGraph adapter.

Parses execution traces from LangGraph graphs (StateGraph / CompiledGraph)
into an AgentRun.

Expected trace shape:

    {
      "_source": "langgraph",
      "graph_id": "research_graph",
      "input": {"task": "the task"},
      "node_executions": [
        {"node": "planner", "input": {...}, "output": {"plan": "..."}},
        {"node": "tools",
         "tool_calls": [
           {"name": "web_search", "args": {"query": "..."},
            "output": "result", "status": "success"}
         ]},
        {"node": "agent", "output": {"messages": [{"content": "..."}]}}
      ],
      "transfers": [
        {"from": "supervisor", "to": "researcher", "reason": "...",
         "context": "...", "next_action": "..."}
      ],
      "final_state": {"output": "final answer"}
    }

Notes:
- Conditional-edge transfers between named subgraphs/agents map to Handoff.
- ToolNode invocations map to ToolCall.

Reference: https://langchain-ai.github.io/langgraph/
"""

from __future__ import annotations

from typing import Any

from ninja_harness.adapters.base import TraceAdapter
from ninja_harness.schemas import AgentRun, AgentStep, Handoff, ToolCall


class LangGraphAdapter(TraceAdapter):
    """Parses LangGraph execution traces into an AgentRun."""

    def can_parse(self, raw: dict) -> bool:
        if raw.get("_source") == "langgraph":
            return True
        return "node_executions" in raw and ("graph_id" in raw or "final_state" in raw)

    def parse(self, raw: dict) -> AgentRun:
        graph_id = raw.get("graph_id", "langgraph")

        task = self._extract_task(raw.get("input", {}))
        final_output = self._extract_final_output(raw.get("final_state", {}))
        if final_output is None:
            raise ValueError(
                "LangGraph trace missing a final output. Expected "
                "final_state.output (or final_state.messages)."
            )

        steps: list[AgentStep] = []
        tool_calls: list[ToolCall] = []

        for node_exec in raw.get("node_executions", []):
            node_name = node_exec.get("node", "node")

            if "tool_calls" in node_exec:
                for tc in node_exec["tool_calls"]:
                    tool_calls.append(
                        ToolCall(
                            tool_name=tc.get("name", "unknown_tool"),
                            arguments=tc.get("args", tc.get("arguments", {})),
                            result=str(tc["output"]) if tc.get("output") is not None else None,
                            status=tc.get("status", "success"),
                            error=tc.get("error"),
                        )
                    )
                steps.append(
                    AgentStep(
                        agent_name=node_name,
                        step_type="action",
                        output=f"ToolNode executed {len(node_exec['tool_calls'])} tool call(s)",
                        status="completed",
                    )
                )
            else:
                output = self._stringify_node_output(node_exec.get("output"))
                steps.append(
                    AgentStep(
                        agent_name=node_name,
                        step_type=self._infer_step_type(node_name),
                        input=self._stringify_node_output(node_exec.get("input")),
                        output=output,
                        status=node_exec.get("status", "completed"),
                        error=node_exec.get("error"),
                    )
                )

        handoffs = [self._parse_transfer(t, raw) for t in raw.get("transfers", [])]

        return AgentRun(
            agent_name=graph_id,
            task=task,
            final_output=final_output,
            steps=steps,
            tool_calls=tool_calls,
            handoffs=handoffs,
            metadata={"adapter": "langgraph"},
        )

    def _extract_task(self, input_state: Any) -> str:
        if isinstance(input_state, dict):
            for key in ("task", "input", "query", "question"):
                if key in input_state:
                    return str(input_state[key])
            if "messages" in input_state and input_state["messages"]:
                first = input_state["messages"][0]
                if isinstance(first, dict):
                    return str(first.get("content", ""))
        return str(input_state) if input_state else ""

    def _extract_final_output(self, final_state: Any) -> str | None:
        if isinstance(final_state, dict):
            for key in ("output", "answer", "result", "final_output"):
                if key in final_state:
                    return str(final_state[key])
            if "messages" in final_state and final_state["messages"]:
                last = final_state["messages"][-1]
                if isinstance(last, dict):
                    return str(last.get("content", ""))
        elif final_state:
            return str(final_state)
        return None

    def _stringify_node_output(self, output: Any) -> str | None:
        if output is None:
            return None
        if isinstance(output, dict):
            if "messages" in output and output["messages"]:
                last = output["messages"][-1]
                if isinstance(last, dict):
                    return str(last.get("content", ""))
            for key in ("output", "plan", "result", "answer"):
                if key in output:
                    return str(output[key])
            return str(output)
        return str(output)

    def _infer_step_type(self, node_name: str) -> str:
        lowered = node_name.lower()
        if "plan" in lowered:
            return "plan"
        if "tool" in lowered:
            return "action"
        if "observ" in lowered or "retriev" in lowered:
            return "observation"
        return "action"

    def _parse_transfer(self, t: dict, raw: dict) -> Handoff:
        return Handoff(
            source_agent=t.get("from", ""),
            target_agent=t.get("to", ""),
            reason=t.get("reason", ""),
            context_summary=t.get("context", t.get("context_summary", "")),
            expected_next_action=t.get("next_action", t.get("expected_next_action", "")),
            task_id=raw.get("task_id"),
            trace_id=raw.get("graph_id"),
        )
