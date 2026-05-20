"""
OpenAI Agents SDK adapter — PLACEHOLDER (v0.2).

Status: NOT IMPLEMENTED.

This adapter will parse traces produced by the OpenAI Agents SDK
(openai.agents.Agent, Runner, handoff, function_tool, etc.).

Expected mapping (v0.2 target):

  OpenAI Agents SDK field        → AgentRun / AgentStep field
  ─────────────────────────────────────────────────────────────
  agent.name                     → agent_name
  run.input / run.output         → task / final_output
  RunStep (message_creation)     → AgentStep(step_type="action")
  RunStep (tool_calls)           → ToolCall list
  handoff(agent=...)             → Handoff
  input_guardrail / output_guard → GuardrailEvent
  usage (prompt/completion)      → token_usage

Reference:
  https://openai.github.io/openai-agents-python/
  https://platform.openai.com/docs/guides/agents

To contribute this adapter:
  1. Implement can_parse() to detect the SDK trace format.
  2. Implement parse() mapping the fields above.
  3. Add integration tests in tests/test_openai_agents_adapter.py.
  4. Remove this docstring placeholder note.
"""

from __future__ import annotations

from ninja_harness.adapters.base import TraceAdapter
from ninja_harness.schemas import AgentRun


class OpenAIAgentsAdapter(TraceAdapter):
    """Placeholder adapter for OpenAI Agents SDK traces. Not yet implemented."""

    def can_parse(self, raw: dict) -> bool:
        # Detect traces that look like they came from the OpenAI Agents SDK.
        # Heuristic: presence of "openai_agents" source marker or SDK-specific fields.
        return raw.get("_source") == "openai_agents_sdk" or (
            "agent_id" in raw and "thread_id" in raw and "run_id" in raw
        )

    def parse(self, raw: dict) -> AgentRun:
        raise NotImplementedError(
            "OpenAIAgentsAdapter is a placeholder and not yet implemented. "
            "This adapter is planned for v0.2. "
            "Please convert your trace to the Ninja Harness Custom JSON format "
            "or contribute the adapter — see docs/architecture.md."
        )
