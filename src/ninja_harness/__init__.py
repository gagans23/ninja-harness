"""Ninja Harness — trace-first evals for agents that need to survive production."""

from ninja_harness.schemas import (
    AgentRun,
    AgentStep,
    EvaluationCase,
    EvaluationResult,
    GuardrailEvent,
    Handoff,
    MetricResult,
    SuiteCaseSpec,
    SuiteResult,
    SuiteSpec,
    ToolCall,
)

__version__ = "0.3.0"
__all__ = [
    "AgentRun",
    "AgentStep",
    "EvaluationCase",
    "EvaluationResult",
    "GuardrailEvent",
    "Handoff",
    "MetricResult",
    "SuiteCaseSpec",
    "SuiteResult",
    "SuiteSpec",
    "ToolCall",
    "__version__",
]
