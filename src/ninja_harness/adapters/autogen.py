"""
AutoGen adapter — PLACEHOLDER (v0.2).

Status: NOT IMPLEMENTED.

This adapter will parse conversation traces produced by Microsoft AutoGen
(AssistantAgent, UserProxyAgent, GroupChatManager, etc.).

Expected mapping (v0.2 target):

  AutoGen concept                → AgentRun / AgentStep field
  ─────────────────────────────────────────────────────────────
  initial_message content        → task
  last assistant message         → final_output
  agent.name                     → agent_name
  message exchange records       → AgentStep list
  function_call in messages      → ToolCall
  agent-to-agent messages        → Handoff (source/target = agent names)

Reference:
  https://microsoft.github.io/autogen/

To contribute this adapter:
  1. Implement can_parse() to detect AutoGen chat history format.
  2. Parse message histories into AgentStep sequences.
  3. Extract function_call blocks as ToolCall entries.
  4. Map agent routing messages to Handoff.
  5. Add tests in tests/test_autogen_adapter.py.
  6. Remove this placeholder docstring note.
"""

from __future__ import annotations

from ninja_harness.adapters.base import TraceAdapter
from ninja_harness.schemas import AgentRun


class AutoGenAdapter(TraceAdapter):
    """Placeholder adapter for AutoGen conversation traces. Not yet implemented."""

    def can_parse(self, raw: dict) -> bool:
        return raw.get("_source") == "autogen" or (
            "chat_history" in raw
            and isinstance(raw.get("chat_history"), list)
        )

    def parse(self, raw: dict) -> AgentRun:
        raise NotImplementedError(
            "AutoGenAdapter is a placeholder and not yet implemented. "
            "This adapter is planned for v0.2. "
            "Please convert your trace to the Ninja Harness Custom JSON format "
            "or contribute the adapter — see docs/architecture.md."
        )
