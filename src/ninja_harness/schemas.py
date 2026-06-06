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


class ReliabilityStats(BaseModel):
    """
    Statistical summary across N repeated runs of the same task.

    Agents are stochastic, so a single run's score is not a reliable estimate
    of production behavior. These statistics quantify central tendency,
    spread, and consistency across repeated trials.
    """

    trials: int
    mean_score: float  # mean NARI score (0-100)
    std_score: float
    min_score: float
    max_score: float
    ci_low: float  # 95% confidence interval lower bound on mean_score
    ci_high: float  # 95% confidence interval upper bound on mean_score
    pass_at_k: float  # P(at least one of k trials certifies PASS)
    pass_hat_k: float  # P(all k trials certify PASS) — the reliability metric
    consistency: float  # 1 - normalized std; 1.0 = perfectly consistent
    certification_distribution: dict[str, int] = Field(default_factory=dict)


class AggregateResult(BaseModel):
    """Aggregated reliability report over repeated evaluations of one task."""

    task_label: str
    reliability: ReliabilityStats
    run_ids: list[str] = Field(default_factory=list)
    per_metric_mean: dict[str, float] = Field(default_factory=dict)
    verdict: str = "UNKNOWN"  # RELIABLE | FLAKY | UNRELIABLE
    notes: list[str] = Field(default_factory=list)


class MetricThreshold(BaseModel):
    """A minimum acceptable score for a single metric."""

    metric: str
    min_score: float  # 0.0 - 1.0


class EvaluationPolicy(BaseModel):
    """
    A configurable gate policy: per-metric minimums and overall thresholds.

    Lets teams define their own acceptance criteria instead of relying solely
    on the built-in certification rules. Used by the `gate` command.
    """

    name: str = "default-policy"
    min_ninja_score: float | None = None  # 0-100
    min_safety_score: float | None = None  # 0-1
    required_certification: str | None = None  # PASS | WARN | FAIL (minimum)
    metric_thresholds: list[MetricThreshold] = Field(default_factory=list)
    max_score_regression: float | None = None  # max allowed drop vs baseline (0-100)
    fail_on_redteam_findings: bool = True


class GateViolation(BaseModel):
    """A single policy violation discovered by the gate."""

    rule: str
    detail: str
    severity: str = "error"  # error | warning


class GateResult(BaseModel):
    """Outcome of applying an EvaluationPolicy to a run."""

    policy_name: str
    passed: bool
    violations: list[GateViolation] = Field(default_factory=list)


class ToolSpec(BaseModel):
    """A tool made available to an agent during a run."""

    name: str
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)


class TaskSpec(BaseModel):
    """
    A runnable task: the prompt to give the agent, the tools it may use, and
    (optionally) the eval case it will be graded against. Consumed by the
    `run` command to drive an agent end to end.
    """

    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    prompt: str
    tools: list[ToolSpec] = Field(default_factory=list)
    eval_case: EvaluationCase | None = None
    max_steps: int | None = None
    sandbox: str = "none"  # none | local | docker
    sandbox_image: str | None = None  # for docker sandbox
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunManifest(BaseModel):
    """
    Reproducibility manifest captured when an agent is run through the harness.

    Records enough provenance to reproduce (or at least audit) a run: tool
    versions, platform, git SHA, the seed used, and a content hash of the
    captured trace.
    """

    ninja_harness_version: str
    python_version: str
    platform: str
    created_at: datetime
    solver: str
    sandbox: str
    seed: int | None = None
    git_sha: str | None = None
    trace_sha256: str = ""
    package_versions: dict[str, str] = Field(default_factory=dict)


class RunReport(BaseModel):
    """The complete output of a `run`: trace + evaluation + provenance."""

    task_id: str
    run: AgentRun
    result: EvaluationResult
    manifest: RunManifest


class HumanLabel(BaseModel):
    """A human judgement of one run, used to calibrate automated judges."""

    run_id: str
    metric: str = "goal_success"  # which dimension was judged, or "overall"
    human_score: float  # 0.0 - 1.0
    annotator: str = "unknown"
    notes: str = ""


class CalibrationReport(BaseModel):
    """
    Agreement between automated judge scores and human labels.

    Keeps judges honest: if correlation/agreement drifts, recalibrate or swap
    the judge. Built from matched (judge_score, human_score) pairs.
    """

    n: int
    metric: str
    mean_abs_error: float
    agreement_within_tolerance: float  # fraction of pairs within `tolerance`
    tolerance: float
    pearson: float | None = None
    spearman: float | None = None
    cohen_kappa: float | None = None  # binary pass/fail at 0.5 threshold
    notes: list[str] = Field(default_factory=list)


class MetricDelta(BaseModel):
    """Change in one metric between a baseline and a current run."""

    name: str
    baseline_score: float | None = None
    current_score: float | None = None
    delta: float | None = None
    status: str = "unchanged"  # improved | regressed | unchanged | added | removed | na


class TrajectoryExample(BaseModel):
    """One graded agent run serialized for model training.

    Ninja Harness *grades* runs; this turns the high-scoring ones into a curated
    training example. The score/certification travel with the example so the
    training set is honestly filtered, never fabricated.
    """

    run_id: str
    task: str
    ninja_score: float
    certification: str
    format: str  # messages | sft
    messages: list[dict[str, Any]] = Field(default_factory=list)  # format == messages
    prompt: str | None = None  # format == sft
    completion: str | None = None  # format == sft
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrajectoryExportSummary(BaseModel):
    """Summary of a trajectory export: how many runs qualified vs. were filtered."""

    total_candidates: int
    exported: int
    skipped: int
    format: str
    min_score: float
    require_pass: bool
    by_certification: dict[str, int] = Field(default_factory=dict)


class DiffReport(BaseModel):
    """Comparison of two EvaluationResults (baseline vs current)."""

    baseline_run_id: str
    current_run_id: str
    baseline_score: float
    current_score: float
    score_delta: float
    baseline_certification: str
    current_certification: str
    certification_changed: bool
    metric_deltas: list[MetricDelta] = Field(default_factory=list)
    regressions: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)

    @property
    def has_regression(self) -> bool:
        return bool(self.regressions) or self.score_delta < 0
