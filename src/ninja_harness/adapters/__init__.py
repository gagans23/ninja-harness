"""Trace adapters — convert framework-native traces into AgentRun."""

from ninja_harness.adapters.autogen import AutoGenAdapter
from ninja_harness.adapters.base import TraceAdapter
from ninja_harness.adapters.crewai import CrewAIAdapter
from ninja_harness.adapters.custom_json import CustomJsonAdapter
from ninja_harness.adapters.hermes import HermesAdapter
from ninja_harness.adapters.langgraph import LangGraphAdapter
from ninja_harness.adapters.openai_agents import OpenAIAgentsAdapter
from ninja_harness.adapters.opentelemetry import OpenTelemetryAdapter

__all__ = [
    "AutoGenAdapter",
    "CrewAIAdapter",
    "CustomJsonAdapter",
    "HermesAdapter",
    "LangGraphAdapter",
    "OpenAIAgentsAdapter",
    "OpenTelemetryAdapter",
    "TraceAdapter",
]

# Registry in priority order — first adapter whose can_parse() returns True is used.
ADAPTER_REGISTRY: list[TraceAdapter] = [
    CustomJsonAdapter(),
    OpenAIAgentsAdapter(),
    LangGraphAdapter(),
    HermesAdapter(),
    CrewAIAdapter(),
    AutoGenAdapter(),
    OpenTelemetryAdapter(),
]


def detect_adapter(raw: dict) -> TraceAdapter:
    """Return the first registered adapter that can parse *raw*."""
    for adapter in ADAPTER_REGISTRY:
        if adapter.can_parse(raw):
            return adapter
    raise ValueError(
        "No adapter could parse this trace. Ensure it matches a supported format "
        "or use the CustomJsonAdapter schema. See docs/architecture.md."
    )
