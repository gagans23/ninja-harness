"""Pydantic v2 data models for Ninja Harness."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """A single tool invocation within an agent run."""

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: Optional[str] = None
    status: str = "unknown"  # success | failed | unknown
    error: Optional[str] = None
    timestamp: Optional[datetime] = None


class AgentStep(BaseModel):
    """One discrete step in an agent's execution trajectory."""

    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str
    step_type: str  # plan | action | observation | handoff | guardrail | final
    input: Optional[str] = None
    output: Optional[str] = None
    status: str = "completed"  # completed | failed | skipped
    error: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Handoff(BaseModel):
    """A transfer of control between two agents."""

    source_agent: str
    target_agent: str
    reason: str
    context_summary: str
    expected_next_action: str
    task_id: Optional[str] = None
    trace_id: Optional[str] = None
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
    expected_output: Optional[str] = None
    steps: list[AgentStep] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    handoffs: list[Handoff] = Field(default_factory=list)
    guardrail_events: list[GuardrailEvent] = Field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    token_usage: Optional[dict[str, Any]] = None
    cost: Optional[float] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def latency_seconds(self) -> Optional[float]:
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
    expected_output: Optional[str] = None
    expected_tool_calls: list[ToolCall] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    safety_requirements: list[str] = Field(default_factory=list)
    max_steps: Optional[int] = None
    max_tool_calls: Optional[int] = None
    max_latency_seconds: Optional[float] = None
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
    case_id: Optional[str] = None
    metric_results: list[MetricResult] = Field(default_factory=list)
    ninja_score: float  # 0–100
    grade: str  # A | B | C | D | F
    certification: str  # PASS | WARN | FAIL
    top_failure_reasons: list[str] = Field(default_factory=list)
    recommended_fixes: list[str] = Field(default_factory=list)

    def metric_by_name(self, name: str) -> Optional[MetricResult]:
        for m in self.metric_results:
            if m.name == name:
                return m
        return None
