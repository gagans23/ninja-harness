"""Evaluation pipeline orchestrator."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ninja_harness.adapters import detect_adapter
from ninja_harness.datasets.loader import load_eval_case, load_trace
from ninja_harness.schemas import AgentRun, EvaluationCase, EvaluationResult
from ninja_harness.scoring.ninja_score import NinjaScoreAggregator


class EvaluationRunner:
    """
    Orchestrates the full evaluation pipeline:

    1. Load raw trace from file.
    2. Auto-detect and apply the appropriate adapter.
    3. Load optional EvaluationCase.
    4. Run all scorers via NinjaScoreAggregator.
    5. Return EvaluationResult.
    """

    def __init__(self, baseline_path: Optional[str] = None) -> None:
        self._aggregator = NinjaScoreAggregator(baseline_path=baseline_path)

    def run_from_files(
        self,
        trace_path: str | Path,
        case_path: Optional[str | Path] = None,
    ) -> tuple[AgentRun, Optional[EvaluationCase], EvaluationResult]:
        raw = load_trace(trace_path)
        adapter = detect_adapter(raw)
        run = adapter.parse(raw)

        case: Optional[EvaluationCase] = None
        if case_path:
            case = load_eval_case(case_path)
            # Sync expected_output into run if not already set
            if case.expected_output and not run.expected_output:
                run = run.model_copy(update={"expected_output": case.expected_output})

        result = self._aggregator.evaluate(run, case)
        return run, case, result

    def run_from_objects(
        self,
        run: AgentRun,
        case: Optional[EvaluationCase] = None,
    ) -> EvaluationResult:
        return self._aggregator.evaluate(run, case)
