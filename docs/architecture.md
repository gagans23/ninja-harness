# Architecture

## Overview

Ninja Harness is organized around three separable concerns:

1. **Ingestion** — convert a framework-native trace into a canonical `AgentRun`
2. **Evaluation** — run scoring metrics against the `AgentRun`
3. **Reporting** — render results as human-readable output or machine-readable JSON

```
Raw trace file
      │
      ▼
 TraceAdapter.detect_adapter()
      │  (selects CustomJsonAdapter, LangGraphAdapter, etc.)
      ▼
    AgentRun          ←── EvaluationCase (optional)
      │                        │
      └──────────┬─────────────┘
                 ▼
      NinjaScoreAggregator
         │
         ├── GoalSuccessScorer
         ├── ToolCallF1Scorer
         ├── HandoffIntegrityScorer
         ├── GroundingScorer
         ├── SafetyScorer
         ├── EfficiencyScorer
         ├── RecoveryScorer
         └── StabilityScorer
                 │
                 ▼
          EvaluationResult
                 │
      ┌──────────┴──────────┐
      ▼                     ▼
  Rich terminal          JSON / Markdown
```

---

## Key Types

### AgentRun

The canonical representation of one agent execution. All adapters produce this.

```python
class AgentRun(BaseModel):
    run_id: str
    agent_name: str
    task: str
    final_output: str
    steps: list[AgentStep]
    tool_calls: list[ToolCall]
    handoffs: list[Handoff]
    guardrail_events: list[GuardrailEvent]
    ...
```

### EvaluationCase

Describes what a *correct* run should look like — expected output, expected tool calls, reference documents, safety requirements, and resource limits.

### MetricResult

Each scorer returns one `MetricResult`:
- `score`: float in [0.0, 1.0], or -1.0 if not applicable
- `passed`: bool
- `details`: structured breakdown
- `failure_reasons` / `recommendations`: human-readable strings

### EvaluationResult

Aggregated output: all metric results + composite NARI score + grade + certification.

---

## Adding a New Adapter

1. Create `src/ninja_harness/adapters/my_framework.py`
2. Subclass `TraceAdapter` and implement `can_parse()` and `parse()`
3. Register it in `adapters/__init__.py` ADAPTER_REGISTRY (before `CustomJsonAdapter` if it should take priority)
4. Add tests in `tests/test_my_framework_adapter.py`

### can_parse() heuristics

`can_parse()` should check for framework-specific fields without loading the full schema — it must be cheap and O(1). Use top-level key presence checks:

```python
def can_parse(self, raw: dict) -> bool:
    return "graph_id" in raw and "node_executions" in raw
```

### parse() contract

- Must return a valid `AgentRun`
- Must raise `ValueError` with a descriptive message if required fields are missing
- Must **not** make network calls, access files, or have side effects
- Must be deterministic

---

## Adding a New Scorer

1. Create `src/ninja_harness/scoring/my_metric.py`
2. Subclass `BaseScorer` and implement `name` and `score()`
3. Add the scorer to `NinjaScoreAggregator._scorers` in `ninja_score.py`
4. Add a weight to `_WEIGHTS` (ensure weights still sum to 1.0)
5. Export from `scoring/__init__.py`
6. Add tests

### BaseScorer contract

```python
class BaseScorer(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def score(self, run: AgentRun, case: Optional[EvaluationCase]) -> MetricResult: ...
```

Return `self._not_applicable("reason")` when the metric cannot be evaluated (no expected output, no handoffs, etc.). The aggregator redistributes weight away from non-applicable metrics.

---

## Scoring weight redistribution

When a metric is not applicable (`score == -1.0`), its weight is excluded from the denominator when computing the composite NARI score. This means scores are always computed over the applicable subset of metrics, not penalised for missing data.

---

## Red Team Module

Red-team detectors live in `src/ninja_harness/redteam/`. They scan trace text fields for risky patterns using compiled regex. They are:

- **Detection-only** — they never generate harmful content
- **Stateless** — each `detect(run_dict)` call is independent
- **Additive** — add new detectors by subclassing (no base class required; ducks-type check only)

The `run_all_checks(run_dict)` function in `redteam/__init__.py` is the single entry point for the CLI.
