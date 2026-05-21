"""
Multi-turn user simulator.

Conversational agents are evaluated against a *simulated user* that plays out a
scenario over several turns (the tau-bench pattern). This module provides the
user-side abstraction and a dialogue driver that captures the conversation as an
AgentRun for scoring.

- UserSimulator: produces the next user message given the history.
- ScriptedUserSimulator: deterministic, replays a fixed list of user turns.
- CallableUserSimulator: wraps a model callable (you supply the model — no LLM
  is bundled). Lets an LLM play the user.
- run_dialogue(): alternates user <-> agent for up to max_turns and returns the
  captured AgentRun.

Ninja Harness ships no model. The scripted simulator keeps tests and demos fully
deterministic; the callable simulator is the hook for an LLM-played user.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from ninja_harness.schemas import AgentRun, AgentStep

# A turn in the running conversation: {"role": "user"|"assistant", "content": str}
Message = dict[str, str]


@runtime_checkable
class UserSimulator(Protocol):
    """Produces the next user message given the conversation so far."""

    name: str

    def next_message(self, history: list[Message]) -> tuple[str | None, bool]:
        """Return (message, done). message=None signals the conversation is over."""
        ...


class ScriptedUserSimulator:
    """Replays a fixed list of user turns. Deterministic."""

    name = "scripted_user"

    def __init__(self, turns: list[str]) -> None:
        self._turns = turns
        self._index = 0

    def next_message(self, history: list[Message]) -> tuple[str | None, bool]:
        if self._index >= len(self._turns):
            return None, True
        msg = self._turns[self._index]
        self._index += 1
        done = self._index >= len(self._turns)
        return msg, done


class CallableUserSimulator:
    """
    Wraps a user-message generator: fn(history) -> (message, done).

    Use this to let an LLM play the user. You provide the callable; the harness
    makes no model calls itself.
    """

    name = "callable_user"

    def __init__(self, fn: Callable[[list[Message]], tuple[str | None, bool]]) -> None:
        self._fn = fn

    def next_message(self, history: list[Message]) -> tuple[str | None, bool]:
        return self._fn(history)


# An agent in a dialogue: given the latest user message + full history, returns a reply.
AgentFn = Callable[[str, list[Message]], str]


def run_dialogue(
    agent_fn: AgentFn,
    simulator: UserSimulator,
    agent_name: str = "Agent",
    task: str = "",
    max_turns: int = 10,
) -> AgentRun:
    """
    Drive a multi-turn conversation between *agent_fn* and *simulator*, returning
    the captured AgentRun. The agent's last reply becomes final_output.
    """
    history: list[Message] = []
    steps: list[AgentStep] = []
    final_output = ""
    first_user_msg = ""

    for _ in range(max_turns):
        user_msg, done = simulator.next_message(history)
        if user_msg is None:
            break
        if not first_user_msg:
            first_user_msg = user_msg

        history.append({"role": "user", "content": user_msg})
        steps.append(
            AgentStep(agent_name="user", step_type="observation", input=user_msg, status="completed")
        )

        reply = agent_fn(user_msg, history)
        history.append({"role": "assistant", "content": reply})
        steps.append(
            AgentStep(agent_name=agent_name, step_type="action", output=reply, status="completed")
        )
        final_output = reply

        if done:
            break

    return AgentRun(
        agent_name=agent_name,
        task=task or first_user_msg,
        final_output=final_output,
        steps=steps,
        metadata={"dialogue_turns": len([m for m in history if m["role"] == "user"])},
    )
