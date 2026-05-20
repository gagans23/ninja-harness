"""
LangGraph adapter — PLACEHOLDER (v0.2).

Status: NOT IMPLEMENTED.

This adapter will parse execution traces / state snapshots produced by
LangGraph graphs (StateGraph, CompiledGraph, etc.).

Expected mapping (v0.2 target):

  LangGraph concept              → AgentRun / AgentStep field
  ─────────────────────────────────────────────────────────────
  graph.name                     → agent_name
  State["task"] / initial input  → task
  State["output"] / final node   → final_output
  Node execution record          → AgentStep(step_type="action")
  ToolNode invocations           → ToolCall list
  Interrupt / transfer edge      → Handoff (source/target = node names)
  Conditional edge outcome       → AgentStep(step_type="observation")

Reference:
  https://langchain-ai.github.io/langgraph/

To contribute this adapter:
  1. Implement can_parse() (detect "langgraph" key or graph_id).
  2. Map node execution records to AgentStep.
  3. Map ToolNode calls to ToolCall.
  4. Add tests in tests/test_langgraph_adapter.py.
  5. Remove this placeholder docstring note.
"""

from __future__ import annotations

from ninja_harness.adapters.base import TraceAdapter
from ninja_harness.schemas import AgentRun


class LangGraphAdapter(TraceAdapter):
    """Placeholder adapter for LangGraph traces. Not yet implemented."""

    def can_parse(self, raw: dict) -> bool:
        return raw.get("_source") == "langgraph" or (
            "graph_id" in raw and "node_executions" in raw
        )

    def parse(self, raw: dict) -> AgentRun:
        raise NotImplementedError(
            "LangGraphAdapter is a placeholder and not yet implemented. "
            "This adapter is planned for v0.2. "
            "Please convert your trace to the Ninja Harness Custom JSON format "
            "or contribute the adapter — see docs/architecture.md."
        )
