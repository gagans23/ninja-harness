"""Pydantic v2 data models for Ninja Harness."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """A single tool invocation within an agent run."""

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: str | None = None
    status: str = "unknown"  # success | failed | unknown
    error: str | None = None
    timestamp: datetime | None = None


class AgentStep(BaseModel):
    """One discrete step in an agent's execution trajectory."""

    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str
    step_type: str  # plan | action | observation | handoff | guardrail | final
    input: str | None = None
    output: str | None = None
    status: str = "completed"  # completed | failed | skipped
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Handoff(BaseModel):
    """A transfer of control between two agents."""

    source_agent: str
    target_agent: str
    reason: str
    context_summary: str
    expected_next_action: str
    task_id: str | None = None
    trace_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GuardrailEvent(BaseModel):
    """A guardrail check result recorded during an agent run."""

    guardrail_name: str
    status: str  # triggered | passed | bypassed
    message: str
    severity: str  # low | medium | high | critical
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentRun(BaseModel):
    """The full execution record for a single agent run."""

    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str
    task: str
    final_output: str
    expected_output: str | None = None
    steps: list[AgentStep] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    handoffs: list[Handoff] = Field(default_factory=list)
    guardrail_events: list[GuardrailEvent] = Field(default_factory=list)
    start_time: datetime | None = None
    end_time: datetime | None = None
    token_usage: dict[str, Any] | None = None
    cost: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def latency_seconds(self) -> float | None:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def failed_tool_calls(self) -> list[ToolCall]:
        return [tc for tc in self.tool_calls if tc.status == "failed"]

    @property
    def failed_steps(self) -> list[AgentStep]:
        return [s for s in self.steps if s.status == "failed"]


class EvaluationCase(BaseModel):
    """Describes what a correct agent run should look like."""

    case_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task: str
    expected_output: str | None = None
    expected_tool_calls: list[ToolCall] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    safety_requirements: list[str] = Field(default_factory=list)
    max_steps: int | None = None
    max_tool_calls: int | None = None
    max_latency_seconds: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MetricResult(BaseModel):
    """The result of a single evaluation metric."""

    name: str
    score: float  # 0.0 – 1.0, or -1.0 when not applicable
    passed: bool
    details: dict[str, Any] = Field(default_factory=dict)
    failure_reasons: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    @property
    def is_applicable(self) -> bool:
        return self.score >= 0.0


class EvaluationResult(BaseModel):
    """The aggregated outcome of evaluating one agent run."""

    run_id: str
    case_id: str | None = None
    metric_results: list[MetricResult] = Field(default_factory=list)
    ninja_score: float  # 0–100
    grade: str  # A | B | C | D | F
    certification: str  # PASS | WARN | FAIL
    top_failure_reasons: list[str] = Field(default_factory=list)
    recommended_fixes: list[str] = Field(default_factory=list)

    def metric_by_name(self, name: str) -> MetricResult | None:
        for m in self.metric_results:
            if m.name == name:
                return m
        return None


class SuiteCaseSpec(BaseModel):
    """One entry in an evaluation suite: a trace and an optional eval case."""

    name: str | None = None
    trace: str  # path to the trace JSON
    case: str | None = None  # path to the eval case YAML/JSON


class SuiteSpec(BaseModel):
    """A named collection of trace/case pairs to evaluate together."""

    name: str = "Ninja Harness Suite"
    description: str | None = None
    baseline: str | None = None
    cases: list[SuiteCaseSpec] = Field(default_factory=list)


class SuiteResult(BaseModel):
    """Aggregated results for a full suite run."""

    name: str
    results: list[EvaluationResult] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.certification == "PASS")

    @property
    def warned(self) -> int:
        return sum(1 for r in self.results if r.certification == "WARN")

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.certification == "FAIL")

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def average_score(self) -> float:
        if not self.results:
            return 0.0
        return round(sum(r.ninja_score for r in self.results) / self.total, 2)
