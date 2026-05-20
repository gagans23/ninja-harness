#!/usr/bin/env python3
"""
Example agent for Ninja Harness `run` (CommandSolver protocol).

Contract:
- Reads a TaskSpec JSON from stdin.
- Prints a trace JSON (Custom JSON format) to stdout.

This is a deliberately trivial, dependency-free, fully deterministic "agent"
so the end-to-end `ninja-harness run` loop works out of the box and in CI.
Replace it with your real agent: any program in any language that follows this
stdin->stdout contract can be driven by CommandSolver.
"""

from __future__ import annotations

import json
import sys


def main() -> None:
    raw = sys.stdin.read()
    task = json.loads(raw) if raw.strip() else {}

    prompt = task.get("prompt", "")
    tools = task.get("tools", [])

    steps = [
        {
            "step_id": "s1",
            "agent_name": "EchoAgent",
            "step_type": "plan",
            "output": f"Plan: answer the request — {prompt[:80]}",
            "status": "completed",
        }
    ]
    tool_calls = []

    # If the task offers tools, exercise the first one deterministically.
    if tools:
        tool_name = tools[0].get("name", "echo")
        tool_calls.append(
            {
                "tool_name": tool_name,
                "arguments": {"query": prompt[:120]},
                "result": f"{tool_name} returned a stub result for the prompt.",
                "status": "success",
            }
        )
        steps.append(
            {
                "step_id": "s2",
                "agent_name": "EchoAgent",
                "step_type": "action",
                "output": f"Called tool {tool_name}",
                "status": "completed",
            }
        )

    final_output = f"Here is my answer to: {prompt}"

    trace = {
        "agent_name": "EchoAgent",
        "task": prompt,
        "final_output": final_output,
        "steps": steps,
        "tool_calls": tool_calls,
        "handoffs": [],
        "guardrail_events": [],
        "metadata": {"agent": "echo_agent.py"},
    }
    json.dump(trace, sys.stdout)


if __name__ == "__main__":
    main()
