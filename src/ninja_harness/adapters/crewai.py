"""
CrewAI adapter.

Parses CrewAI execution output (Crew, Agent, Task, Process) into an AgentRun.

Expected trace shape:

    {
      "_source": "crewai",
      "crew_name": "ResearchCrew",
      "agents": [
        {"role": "Researcher", "goal": "find facts"},
        {"role": "Writer", "goal": "draft summary"}
      ],
      "tasks": [
        {"description": "Research transformer efficiency",
         "agent": "Researcher",
         "output": "found FlashAttention, MoE...",
         "tools_used": [
           {"tool": "web_search", "input": {"query": "..."},
            "output": "...", "status": "success"}
         ]},
        {"description": "Write summary", "agent": "Writer",
         "output": "final summary text",
         "delegated_from": "Researcher"}
      ],
      "final_output": "the crew's final result"
    }

Notes:
- Each task maps to one or more AgentSteps.
- tools_used entries map to ToolCall.
- A task's "delegated_from" field maps to a Handoff.

Reference: https://docs.crewai.com/
"""

from __future__ import annotations

from ninja_harness.adapters.base import TraceAdapter
from ninja_harness.schemas import AgentRun, AgentStep, Handoff, ToolCall


class CrewAIAdapter(TraceAdapter):
    """Parses CrewAI crew execution traces into an AgentRun."""

    def can_parse(self, raw: dict) -> bool:
        if raw.get("_source") == "crewai":
            return True
        return "crew_name" in raw and "tasks" in raw

    def parse(self, raw: dict) -> AgentRun:
        crew_name = raw.get("crew_name", "Crew")
        tasks = raw.get("tasks", [])

        if "final_output" in raw:
            final_output = str(raw["final_output"])
        elif tasks and tasks[-1].get("output"):
            final_output = str(tasks[-1]["output"])
        else:
            raise ValueError(
                "CrewAI trace missing final output. Expected 'final_output' "
                "or an output on the last task."
            )

        task_description = tasks[0]["description"] if tasks else raw.get("task", "")

        steps: list[AgentStep] = []
        tool_calls: list[ToolCall] = []
        handoffs: list[Handoff] = []

        for i, task in enumerate(tasks):
            agent_role = task.get("agent", crew_name)

            steps.append(
                AgentStep(
                    agent_name=agent_role,
                    step_type="plan" if i == 0 else "action",
                    input=task.get("description"),
                    output=str(task.get("output", "")),
                    status=task.get("status", "completed"),
                    error=task.get("error"),
                )
            )

            for tool in task.get("tools_used", []):
                tool_calls.append(
                    ToolCall(
                        tool_name=tool.get("tool", tool.get("name", "unknown_tool")),
                        arguments=tool.get("input", tool.get("arguments", {})),
                        result=str(tool["output"]) if tool.get("output") is not None else None,
                        status=tool.get("status", "success"),
                        error=tool.get("error"),
                    )
                )

            delegated_from = task.get("delegated_from")
            if delegated_from:
                handoffs.append(
                    Handoff(
                        source_agent=delegated_from,
                        target_agent=agent_role,
                        reason=task.get("delegation_reason", "CrewAI task delegation"),
                        context_summary=task.get("description", "")[:200],
                        expected_next_action=task.get("description", "")[:200],
                        task_id=task.get("task_id", f"task-{i}"),
                        trace_id=crew_name,
                    )
                )

        return AgentRun(
            agent_name=crew_name,
            task=str(task_description),
            final_output=final_output,
            steps=steps,
            tool_calls=tool_calls,
            handoffs=handoffs,
            metadata={"adapter": "crewai", "agent_count": len(raw.get("agents", []))},
        )
