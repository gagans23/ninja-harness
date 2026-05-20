"""
CrewAI adapter — PLACEHOLDER (v0.2).

Status: NOT IMPLEMENTED.

This adapter will parse execution logs and traces produced by CrewAI
(Crew, Agent, Task, Process objects).

Expected mapping (v0.2 target):

  CrewAI concept                 → AgentRun / AgentStep field
  ─────────────────────────────────────────────────────────────
  crew.kickoff() result          → final_output
  task.description               → task
  agent.role                     → agent_name
  task.output / agent log        → AgentStep list
  tool invocation                → ToolCall
  agent delegation               → Handoff

Reference:
  https://docs.crewai.com/

To contribute this adapter:
  1. Implement can_parse() to detect CrewAI output format.
  2. Map crew task logs to AgentStep and ToolCall.
  3. Map agent delegation events to Handoff.
  4. Add tests in tests/test_crewai_adapter.py.
  5. Remove this placeholder docstring note.
"""

from __future__ import annotations

from ninja_harness.adapters.base import TraceAdapter
from ninja_harness.schemas import AgentRun


class CrewAIAdapter(TraceAdapter):
    """Placeholder adapter for CrewAI traces. Not yet implemented."""

    def can_parse(self, raw: dict) -> bool:
        return raw.get("_source") == "crewai" or (
            "crew_name" in raw and "agents" in raw and "tasks" in raw
        )

    def parse(self, raw: dict) -> AgentRun:
        raise NotImplementedError(
            "CrewAIAdapter is a placeholder and not yet implemented. "
            "This adapter is planned for v0.2. "
            "Please convert your trace to the Ninja Harness Custom JSON format "
            "or contribute the adapter — see docs/architecture.md."
        )
