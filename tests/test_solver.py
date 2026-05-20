"""Tests for solvers and the end-to-end TaskExecutor."""

from __future__ import annotations

import sys

import pytest

from ninja_harness.runner import TaskExecutor
from ninja_harness.schemas import AgentRun, EvaluationCase, RunReport, TaskSpec
from ninja_harness.solver import (
    CallableSolver,
    CommandSolver,
    ScriptedSolver,
    Solver,
)

SIMPLE_TRACE = "src/ninja_harness/examples/simple_agent_trace.json"
ECHO_AGENT = "examples/agents/echo_agent.py"


def make_task() -> TaskSpec:
    return TaskSpec(
        task_id="t1",
        prompt="Summarize transformer efficiency advances.",
        eval_case=EvaluationCase(task="t", expected_output="transformer efficiency advances"),
    )


# --------------------------------------------------------------------------
# ScriptedSolver
# --------------------------------------------------------------------------

def test_scripted_solver_is_a_solver() -> None:
    assert isinstance(ScriptedSolver(trace_path=SIMPLE_TRACE), Solver)


def test_scripted_solver_replays_trace() -> None:
    solver = ScriptedSolver(trace_path=SIMPLE_TRACE)
    run = solver.solve(make_task())
    assert isinstance(run, AgentRun)
    assert run.agent_name == "ResearchAgent"


def test_scripted_solver_requires_input() -> None:
    with pytest.raises(ValueError):
        ScriptedSolver()


# --------------------------------------------------------------------------
# CommandSolver
# --------------------------------------------------------------------------

def test_command_solver_runs_real_agent() -> None:
    solver = CommandSolver([sys.executable, ECHO_AGENT])
    run = solver.solve(make_task())
    assert run.agent_name == "EchoAgent"
    assert "Summarize transformer" in run.final_output


def test_command_solver_empty_command_raises() -> None:
    with pytest.raises(ValueError):
        CommandSolver([])


def test_command_solver_bad_output_raises() -> None:
    solver = CommandSolver([sys.executable, "-c", "print('not json')"])
    with pytest.raises(RuntimeError):
        solver.solve(make_task())


def test_command_solver_nonzero_exit_raises() -> None:
    solver = CommandSolver([sys.executable, "-c", "import sys; sys.exit(1)"])
    with pytest.raises(RuntimeError):
        solver.solve(make_task())


# --------------------------------------------------------------------------
# CallableSolver
# --------------------------------------------------------------------------

def test_callable_solver() -> None:
    def fn(task: TaskSpec, sandbox) -> AgentRun:
        return AgentRun(agent_name="Inproc", task=task.prompt, final_output="done")

    solver = CallableSolver(fn)
    run = solver.solve(make_task())
    assert run.agent_name == "Inproc"


def test_callable_solver_must_return_agentrun() -> None:
    solver = CallableSolver(lambda task, sandbox: "not a run")  # type: ignore[arg-type,return-value]
    with pytest.raises(TypeError):
        solver.solve(make_task())


# --------------------------------------------------------------------------
# TaskExecutor (end-to-end)
# --------------------------------------------------------------------------

def test_executor_end_to_end_with_command_solver() -> None:
    executor = TaskExecutor()
    report = executor.run(make_task(), CommandSolver([sys.executable, ECHO_AGENT]), seed=7)
    assert isinstance(report, RunReport)
    assert report.run.agent_name == "EchoAgent"
    assert report.result.certification in {"PASS", "WARN", "FAIL"}
    assert report.manifest.solver == "command"
    assert report.manifest.seed == 7
    assert len(report.manifest.trace_sha256) == 64


def test_executor_manifest_records_versions() -> None:
    executor = TaskExecutor()
    report = executor.run(make_task(), ScriptedSolver(trace_path=SIMPLE_TRACE))
    assert "pydantic" in report.manifest.package_versions
    assert report.manifest.ninja_harness_version


def test_executor_trace_hash_is_stable() -> None:
    executor = TaskExecutor()
    r1 = executor.run(make_task(), ScriptedSolver(trace_path=SIMPLE_TRACE))
    r2 = executor.run(make_task(), ScriptedSolver(trace_path=SIMPLE_TRACE))
    assert r1.manifest.trace_sha256 == r2.manifest.trace_sha256
