"""Tests for the multi-turn user simulator and dialogue driver."""

from __future__ import annotations

from ninja_harness.schemas import AgentRun
from ninja_harness.simulator import (
    CallableUserSimulator,
    ScriptedUserSimulator,
    UserSimulator,
    run_dialogue,
)


def test_scripted_simulator_is_a_simulator() -> None:
    assert isinstance(ScriptedUserSimulator(["hi"]), UserSimulator)


def test_scripted_simulator_yields_turns_then_done() -> None:
    sim = ScriptedUserSimulator(["a", "b"])
    m1, d1 = sim.next_message([])
    m2, d2 = sim.next_message([])
    m3, d3 = sim.next_message([])
    assert (m1, d1) == ("a", False)
    assert (m2, d2) == ("b", True)
    assert m3 is None and d3 is True


def test_callable_simulator() -> None:
    sim = CallableUserSimulator(lambda history: ("only message", True))
    msg, done = sim.next_message([])
    assert msg == "only message"
    assert done is True


def test_run_dialogue_captures_agentrun() -> None:
    sim = ScriptedUserSimulator(["What is 2+2?", "And times 3?"])

    def agent(user_msg: str, history: list[dict]) -> str:
        return f"reply to: {user_msg}"

    run = run_dialogue(agent, sim, agent_name="Calc", max_turns=10)
    assert isinstance(run, AgentRun)
    assert run.agent_name == "Calc"
    assert run.task == "What is 2+2?"  # first user message
    assert run.final_output == "reply to: And times 3?"
    # 2 user observations + 2 agent actions
    assert len(run.steps) == 4
    assert run.metadata["dialogue_turns"] == 2


def test_run_dialogue_respects_max_turns() -> None:
    sim = ScriptedUserSimulator(["a", "b", "c", "d", "e"])
    run = run_dialogue(lambda m, h: "ok", sim, max_turns=2)
    assert run.metadata["dialogue_turns"] == 2


def test_run_dialogue_stops_when_user_done() -> None:
    sim = CallableUserSimulator(lambda history: ("only", True))
    run = run_dialogue(lambda m, h: "ack", sim, max_turns=10)
    assert run.metadata["dialogue_turns"] == 1
    assert run.final_output == "ack"
