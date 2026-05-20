"""
Hermes multi-agent adapter — PLACEHOLDER (v0.2).

Status: NOT IMPLEMENTED.

This adapter will parse traces produced by Hermes-style multi-agent
orchestration patterns (tool-call-as-handoff, chain-of-thought with
function calling, hierarchical agent delegation).

Expected mapping (v0.2 target):

  Hermes concept                 → AgentRun / AgentStep field
  ─────────────────────────────────────────────────────────────
  root message role=user         → task
  assistant role messages        → AgentStep list
  function_call entries          → ToolCall list
  agent delegation entries       → Handoff
  final assistant message        → final_output

Reference:
  Hermes traces are typically structured as message arrays with
  role/content/function_call fields following the Hermes prompt format.

To contribute this adapter:
  1. Implement can_parse() to detect the Hermes message format.
  2. Parse message arrays into AgentStep and ToolCall sequences.
  3. Detect agent-delegation function calls and map to Handoff.
  4. Add tests in tests/test_hermes_adapter.py.
  5. Remove this placeholder docstring note.
"""

from __future__ import annotations

from ninja_harness.adapters.base import TraceAdapter
from ninja_harness.schemas import AgentRun


class HermesAdapter(TraceAdapter):
    """Placeholder adapter for Hermes-style multi-agent traces. Not yet implemented."""

    def can_parse(self, raw: dict) -> bool:
        return raw.get("_source") == "hermes" or (
            "messages" in raw
            and isinstance(raw.get("messages"), list)
            and any(m.get("role") == "tool" for m in raw.get("messages", []))
        )

    def parse(self, raw: dict) -> AgentRun:
        raise NotImplementedError(
            "HermesAdapter is a placeholder and not yet implemented. "
            "This adapter is planned for v0.2. "
            "Please convert your trace to the Ninja Harness Custom JSON format "
            "or contribute the adapter — see docs/architecture.md."
        )
