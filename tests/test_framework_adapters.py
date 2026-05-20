"""Tests for the v0.2 framework adapters."""

from __future__ import annotations

import pytest

from ninja_harness.adapters import detect_adapter
from ninja_harness.adapters.autogen import AutoGenAdapter
from ninja_harness.adapters.crewai import CrewAIAdapter
from ninja_harness.adapters.hermes import HermesAdapter
from ninja_harness.adapters.langgraph import LangGraphAdapter
from ninja_harness.adapters.openai_agents import OpenAIAgentsAdapter
from ninja_harness.schemas import AgentRun

# --------------------------------------------------------------------------
# OpenAI Agents SDK
# --------------------------------------------------------------------------

def test_openai_can_parse() -> None:
    raw = {"_source": "openai_agents_sdk", "agent": {"name": "A"}, "final_output": "x", "new_items": []}
    assert OpenAIAgentsAdapter().can_parse(raw) is True


def test_openai_parses_tools_and_handoffs() -> None:
    raw = {
        "_source": "openai_agents_sdk",
        "agent": {"name": "TriageAgent"},
        "input": "help me",
        "final_output": "done",
        "new_items": [
            {"type": "handoff_output_item", "source_agent": "TriageAgent", "target_agent": "BillingAgent",
             "reason": "billing", "context_summary": "ctx", "expected_next_action": "refund"},
            {"type": "tool_call_item", "agent": "BillingAgent",
             "raw_item": {"name": "issue_refund", "arguments": {"amount": 20}}},
            {"type": "tool_call_output_item", "agent": "BillingAgent", "output": "refunded"},
        ],
        "usage": {"total_tokens": 100},
    }
    run = OpenAIAgentsAdapter().parse(raw)
    assert isinstance(run, AgentRun)
    assert run.agent_name == "TriageAgent"
    assert len(run.tool_calls) == 1
    assert run.tool_calls[0].tool_name == "issue_refund"
    assert run.tool_calls[0].result == "refunded"
    assert len(run.handoffs) == 1
    assert run.handoffs[0].target_agent == "BillingAgent"
    assert run.token_usage == {"total_tokens": 100}


def test_openai_string_arguments_parsed() -> None:
    raw = {
        "_source": "openai_agents_sdk",
        "agent": {"name": "A"},
        "input": "t",
        "final_output": "o",
        "new_items": [
            {"type": "tool_call_item", "raw_item": {"name": "search", "arguments": "{\"q\": \"hi\"}"}},
            {"type": "tool_call_output_item", "output": "res"},
        ],
    }
    run = OpenAIAgentsAdapter().parse(raw)
    assert run.tool_calls[0].arguments == {"q": "hi"}


def test_openai_missing_final_output_raises() -> None:
    raw = {"_source": "openai_agents_sdk", "agent": {"name": "A"}, "new_items": []}
    with pytest.raises(ValueError):
        OpenAIAgentsAdapter().parse(raw)


# --------------------------------------------------------------------------
# LangGraph
# --------------------------------------------------------------------------

def test_langgraph_can_parse() -> None:
    raw = {"_source": "langgraph", "node_executions": [], "final_state": {"output": "x"}}
    assert LangGraphAdapter().can_parse(raw) is True


def test_langgraph_parses_nodes_and_tools() -> None:
    raw = {
        "_source": "langgraph",
        "graph_id": "g1",
        "input": {"task": "compare cities"},
        "node_executions": [
            {"node": "planner", "output": {"plan": "do it"}},
            {"node": "tools", "tool_calls": [
                {"name": "wiki", "args": {"e": "Tokyo"}, "output": "14M", "status": "success"}
            ]},
        ],
        "transfers": [{"from": "planner", "to": "researcher", "reason": "r", "context": "c", "next_action": "n"}],
        "final_state": {"output": "Tokyo is bigger"},
    }
    run = LangGraphAdapter().parse(raw)
    assert run.agent_name == "g1"
    assert run.task == "compare cities"
    assert run.final_output == "Tokyo is bigger"
    assert len(run.tool_calls) == 1
    assert run.tool_calls[0].tool_name == "wiki"
    assert len(run.handoffs) == 1


def test_langgraph_messages_final_output() -> None:
    raw = {
        "_source": "langgraph",
        "graph_id": "g",
        "input": {"messages": [{"content": "q"}]},
        "node_executions": [],
        "final_state": {"messages": [{"content": "the answer"}]},
    }
    run = LangGraphAdapter().parse(raw)
    assert run.final_output == "the answer"
    assert run.task == "q"


# --------------------------------------------------------------------------
# Hermes
# --------------------------------------------------------------------------

def test_hermes_can_parse() -> None:
    raw = {"messages": [{"role": "tool", "content": "x"}]}
    assert HermesAdapter().can_parse(raw) is True


def test_hermes_parses_messages() -> None:
    raw = {
        "_source": "hermes",
        "agent_name": "Orch",
        "task": "weather?",
        "messages": [
            {"role": "user", "content": "weather?"},
            {"role": "assistant", "agent": "Orch", "content": "checking",
             "tool_calls": [{"function": {"name": "get_weather", "arguments": "{\"city\": \"Paris\"}"}}]},
            {"role": "tool", "name": "get_weather", "content": "rainy"},
            {"role": "assistant", "agent": "Advisor", "content": "bring an umbrella"},
        ],
    }
    run = HermesAdapter().parse(raw)
    assert run.final_output == "bring an umbrella"
    assert len(run.tool_calls) == 1
    assert run.tool_calls[0].result == "rainy"
    assert run.tool_calls[0].arguments == {"city": "Paris"}
    # Handoff inferred between Orch and Advisor
    assert len(run.handoffs) == 1
    assert run.handoffs[0].source_agent == "Orch"
    assert run.handoffs[0].target_agent == "Advisor"


def test_hermes_no_messages_raises() -> None:
    with pytest.raises(ValueError):
        HermesAdapter().parse({"_source": "hermes", "messages": []})


# --------------------------------------------------------------------------
# CrewAI
# --------------------------------------------------------------------------

def test_crewai_can_parse() -> None:
    raw = {"crew_name": "C", "tasks": []}
    assert CrewAIAdapter().can_parse(raw) is True


def test_crewai_parses_tasks_and_delegation() -> None:
    raw = {
        "_source": "crewai",
        "crew_name": "ResearchCrew",
        "agents": [{"role": "Researcher"}, {"role": "Writer"}],
        "tasks": [
            {"description": "research", "agent": "Researcher", "output": "facts",
             "tools_used": [{"tool": "web_search", "input": {"q": "x"}, "output": "r", "status": "success"}]},
            {"description": "write", "agent": "Writer", "output": "summary", "delegated_from": "Researcher"},
        ],
        "final_output": "summary",
    }
    run = CrewAIAdapter().parse(raw)
    assert run.agent_name == "ResearchCrew"
    assert run.final_output == "summary"
    assert len(run.tool_calls) == 1
    assert len(run.handoffs) == 1
    assert run.handoffs[0].source_agent == "Researcher"
    assert run.handoffs[0].target_agent == "Writer"


def test_crewai_final_output_from_last_task() -> None:
    raw = {
        "crew_name": "C",
        "tasks": [{"description": "t", "agent": "A", "output": "last output"}],
    }
    run = CrewAIAdapter().parse(raw)
    assert run.final_output == "last output"


# --------------------------------------------------------------------------
# AutoGen
# --------------------------------------------------------------------------

def test_autogen_can_parse() -> None:
    raw = {"chat_history": [{"name": "a", "role": "user", "content": "x"}]}
    assert AutoGenAdapter().can_parse(raw) is True


def test_autogen_parses_history_and_tools() -> None:
    raw = {
        "_source": "autogen",
        "task": "compute",
        "chat_history": [
            {"name": "user_proxy", "role": "user", "content": "compute"},
            {"name": "assistant", "role": "assistant", "content": "calculating",
             "tool_calls": [{"function": {"name": "calc", "arguments": {"e": "2+2"}}}]},
            {"name": "user_proxy", "role": "tool", "tool_name": "calc", "content": "4"},
            {"name": "assistant", "role": "assistant", "content": "the answer is 4"},
        ],
    }
    run = AutoGenAdapter().parse(raw)
    assert run.final_output == "the answer is 4"
    assert len(run.tool_calls) == 1
    assert run.tool_calls[0].result == "4"


def test_autogen_no_history_raises() -> None:
    with pytest.raises(ValueError):
        AutoGenAdapter().parse({"_source": "autogen", "chat_history": []})


# --------------------------------------------------------------------------
# Adapter auto-detection
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ({"_source": "openai_agents_sdk", "agent": {"name": "A"}, "final_output": "x", "new_items": []}, "OpenAIAgentsAdapter"),
        ({"_source": "langgraph", "node_executions": [], "final_state": {"output": "x"}}, "LangGraphAdapter"),
        ({"_source": "hermes", "messages": [{"role": "tool", "content": "x"}]}, "HermesAdapter"),
        ({"crew_name": "C", "tasks": [{"output": "x"}]}, "CrewAIAdapter"),
        ({"chat_history": [{"role": "user", "content": "x"}]}, "AutoGenAdapter"),
        ({"agent_name": "A", "task": "t", "final_output": "o"}, "CustomJsonAdapter"),
    ],
)
def test_detect_adapter_routes_correctly(raw: dict, expected: str) -> None:
    adapter = detect_adapter(raw)
    assert adapter.adapter_name == expected
