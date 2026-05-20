"""Tests for the OpenTelemetry GenAI adapter."""

from __future__ import annotations

import pytest

from ninja_harness.adapters import detect_adapter
from ninja_harness.adapters.opentelemetry import OpenTelemetryAdapter
from ninja_harness.schemas import AgentRun


def test_can_parse_source_marker() -> None:
    raw = {"_source": "opentelemetry", "spans": [{"attributes": {"gen_ai.operation.name": "chat"}}]}
    assert OpenTelemetryAdapter().can_parse(raw) is True


def test_can_parse_by_gen_ai_attrs() -> None:
    raw = {"spans": [{"name": "x", "attributes": {"gen_ai.request.model": "gpt-4o"}}]}
    assert OpenTelemetryAdapter().can_parse(raw) is True


def test_cannot_parse_without_genai() -> None:
    assert OpenTelemetryAdapter().can_parse({"spans": [{"attributes": {"http.method": "GET"}}]}) is False


def test_parses_agent_tool_and_output() -> None:
    raw = {
        "_source": "opentelemetry",
        "spans": [
            {
                "name": "invoke_agent A",
                "attributes": {
                    "gen_ai.operation.name": "invoke_agent",
                    "gen_ai.agent.name": "SupportAgent",
                    "gen_ai.input.messages": [{"role": "user", "content": "status?"}],
                    "gen_ai.usage.input_tokens": 100,
                },
                "status": {"code": "OK"},
            },
            {
                "name": "execute_tool lookup",
                "attributes": {
                    "gen_ai.operation.name": "execute_tool",
                    "gen_ai.tool.name": "lookup_order",
                    "gen_ai.tool.call.arguments": {"id": "A-1"},
                    "gen_ai.tool.call.result": "shipped",
                },
                "status": {"code": "OK"},
            },
            {
                "name": "invoke_agent A",
                "attributes": {
                    "gen_ai.operation.name": "invoke_agent",
                    "gen_ai.agent.name": "SupportAgent",
                    "gen_ai.output.messages": [{"role": "assistant", "content": "It shipped."}],
                    "gen_ai.usage.output_tokens": 30,
                },
                "status": {"code": "OK"},
            },
        ],
    }
    run = OpenTelemetryAdapter().parse(raw)
    assert isinstance(run, AgentRun)
    assert run.agent_name == "SupportAgent"
    assert run.task == "status?"
    assert run.final_output == "It shipped."
    assert len(run.tool_calls) == 1
    assert run.tool_calls[0].tool_name == "lookup_order"
    assert run.tool_calls[0].result == "shipped"
    assert run.token_usage["total_tokens"] == 130


def test_failed_tool_span_marks_failed() -> None:
    raw = {
        "_source": "opentelemetry",
        "final_output": "done",
        "spans": [
            {
                "name": "execute_tool x",
                "attributes": {"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": "x"},
                "status": {"code": "ERROR"},
            }
        ],
    }
    run = OpenTelemetryAdapter().parse(raw)
    assert run.tool_calls[0].status == "failed"


def test_no_final_output_raises() -> None:
    raw = {
        "_source": "opentelemetry",
        "spans": [
            {"name": "execute_tool x", "attributes": {"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": "x"}}
        ],
    }
    with pytest.raises(ValueError):
        OpenTelemetryAdapter().parse(raw)


def test_no_spans_raises() -> None:
    with pytest.raises(ValueError):
        OpenTelemetryAdapter().parse({"_source": "opentelemetry", "spans": []})


def test_detect_adapter_routes_to_otel() -> None:
    raw = {"_source": "opentelemetry", "final_output": "x",
           "spans": [{"attributes": {"gen_ai.operation.name": "chat"}}]}
    assert detect_adapter(raw).adapter_name == "OpenTelemetryAdapter"
