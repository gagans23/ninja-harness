"""Ninja Harness — trace-first evals for agents that need to survive production."""

from ninja_harness.schemas import (
    AgentRun,
    AgentStep,
    EvaluationCase,
    EvaluationResult,
    GuardrailEvent,
    Handoff,
    MetricResult,
    RunManifest,
    RunReport,
    SuiteCaseSpec,
    SuiteResult,
    SuiteSpec,
    TaskSpec,
    ToolCall,
    ToolSpec,
)

__version__ = "0.5.0"
__all__ = [
    "AgentRun",
    "AgentStep",
    "EvaluationCase",
    "EvaluationResult",
    "GuardrailEvent",
    "Handoff",
    "MetricResult",
    "RunManifest",
    "RunReport",
    "SuiteCaseSpec",
    "SuiteResult",
    "SuiteSpec",
    "TaskSpec",
    "ToolCall",
    "ToolSpec",
    "__version__",
]
