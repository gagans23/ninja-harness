"""
Solver abstraction — drive an agent against a task and capture its trace.

A Solver takes a TaskSpec and returns an AgentRun (the captured trace), which
the harness then evaluates. This is what turns Ninja Harness from a trace
scorer into an end-to-end harness: task in, certified report out.

Three solvers ship:
- ScriptedSolver: replays a fixed trace file. Deterministic; ideal for tests,
  demos, and re-evaluating a previously captured run through the full pipeline.
- CommandSolver: runs an external agent as a subprocess (optionally inside a
  Sandbox). The agent receives the task as JSON on stdin and prints a trace
  JSON to stdout. This drives ANY agent in ANY language — nothing is faked.
- CallableSolver: wraps a Python callable for in-process agents.

Ninja Harness does not ship an LLM-backed agent — you bring the agent. The
solvers here are the real plumbing that connects your agent to the evaluator.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Protocol, runtime_checkable

from ninja_harness.adapters import detect_adapter
from ninja_harness.datasets.loader import load_trace
from ninja_harness.sandbox import LocalSandbox, Sandbox
from ninja_harness.schemas import AgentRun, TaskSpec


@runtime_checkable
class Solver(Protocol):
    """Drives an agent against a task and returns the captured trace."""

    name: str

    def solve(self, task: TaskSpec, sandbox: Sandbox | None = None) -> AgentRun:
        ...


class ScriptedSolver:
    """Returns a fixed, pre-captured trace. Deterministic."""

    name = "scripted"

    def __init__(self, trace_path: str | None = None, run: AgentRun | None = None) -> None:
        if run is not None:
            self._run = run
        elif trace_path is not None:
            raw = load_trace(trace_path)
            self._run = detect_adapter(raw).parse(raw)
        else:
            raise ValueError("ScriptedSolver requires either trace_path or run.")

    def solve(self, task: TaskSpec, sandbox: Sandbox | None = None) -> AgentRun:
        return self._run


class CommandSolver:
    """
    Runs an external agent command. The command receives the task as JSON on
    stdin and must print a trace JSON to stdout (any supported trace format).

    Example:
        CommandSolver(["python", "my_agent.py"])
    """

    name = "command"

    def __init__(self, command: list[str], timeout: float = 120.0) -> None:
        if not command:
            raise ValueError("CommandSolver requires a non-empty command.")
        self._command = command
        self._timeout = timeout

    def solve(self, task: TaskSpec, sandbox: Sandbox | None = None) -> AgentRun:
        sandbox = sandbox or LocalSandbox()
        task_json = task.model_dump_json()
        result = sandbox.exec(self._command, stdin=task_json, timeout=self._timeout)

        if result.timed_out:
            raise RuntimeError(f"Agent command timed out after {self._timeout}s: {self._command}")
        if not result.ok:
            raise RuntimeError(
                f"Agent command failed (exit {result.exit_code}): {self._command}\n"
                f"stderr: {result.stderr[:500]}"
            )

        stdout = result.stdout.strip()
        if not stdout:
            raise RuntimeError("Agent command produced no output; expected a trace JSON on stdout.")

        try:
            raw = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Agent stdout was not valid JSON. The agent must print a trace JSON.\n"
                f"First 300 chars: {stdout[:300]}"
            ) from exc

        return detect_adapter(raw).parse(raw)


class CallableSolver:
    """
    Wraps a Python callable: fn(task, sandbox) -> AgentRun. For in-process
    agents that you can import and call directly.
    """

    name = "callable"

    def __init__(self, fn: Callable[[TaskSpec, Sandbox | None], AgentRun]) -> None:
        self._fn = fn

    def solve(self, task: TaskSpec, sandbox: Sandbox | None = None) -> AgentRun:
        run = self._fn(task, sandbox)
        if not isinstance(run, AgentRun):
            raise TypeError(
                f"CallableSolver fn must return an AgentRun, got {type(run).__name__}."
            )
        return run
