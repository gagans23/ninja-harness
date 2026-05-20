"""Evaluation pipeline orchestrator."""

from __future__ import annotations

import asyncio
import os
import random
from pathlib import Path

from ninja_harness.adapters import detect_adapter
from ninja_harness.datasets.loader import load_eval_case, load_suite, load_trace
from ninja_harness.provenance import build_manifest
from ninja_harness.sandbox import Sandbox, make_sandbox
from ninja_harness.schemas import (
    AgentRun,
    EvaluationCase,
    EvaluationResult,
    RunReport,
    SuiteCaseSpec,
    SuiteResult,
    SuiteSpec,
    TaskSpec,
)
from ninja_harness.scoring.judge import Judge
from ninja_harness.scoring.ninja_score import NinjaScoreAggregator
from ninja_harness.solver import Solver


class EvaluationRunner:
    """
    Orchestrates the full evaluation pipeline:

    1. Load raw trace from file.
    2. Auto-detect and apply the appropriate adapter.
    3. Load optional EvaluationCase.
    4. Run all scorers via NinjaScoreAggregator.
    5. Return EvaluationResult.

    Pass a custom `judge` to change how Goal Success compares outputs.
    """

    def __init__(
        self,
        baseline_path: str | None = None,
        judge: Judge | None = None,
    ) -> None:
        self._aggregator = NinjaScoreAggregator(baseline_path=baseline_path, judge=judge)

    def run_from_files(
        self,
        trace_path: str | Path,
        case_path: str | Path | None = None,
    ) -> tuple[AgentRun, EvaluationCase | None, EvaluationResult]:
        raw = load_trace(trace_path)
        adapter = detect_adapter(raw)
        run = adapter.parse(raw)

        case: EvaluationCase | None = None
        if case_path:
            case = load_eval_case(case_path)
            if case.expected_output and not run.expected_output:
                run = run.model_copy(update={"expected_output": case.expected_output})

        result = self._aggregator.evaluate(run, case)
        return run, case, result

    def run_from_objects(
        self,
        run: AgentRun,
        case: EvaluationCase | None = None,
    ) -> EvaluationResult:
        return self._aggregator.evaluate(run, case)


class SuiteRunner:
    """
    Runs a full evaluation suite (multiple trace/case pairs).

    Provides both a synchronous runner and an async runner that evaluates
    cases concurrently using a worker pool (scoring is CPU-bound and runs in
    threads via asyncio.to_thread).
    """

    def __init__(self, judge: Judge | None = None) -> None:
        self._judge = judge

    def run_suite(self, spec: SuiteSpec) -> SuiteResult:
        results: list[EvaluationResult] = []
        errors: list[dict] = []
        runner = EvaluationRunner(baseline_path=spec.baseline, judge=self._judge)

        for case_spec in spec.cases:
            try:
                _, _, result = runner.run_from_files(case_spec.trace, case_spec.case)
                results.append(result)
            except Exception as exc:  # noqa: BLE001 - collect, don't abort the suite
                errors.append(
                    {"trace": case_spec.trace, "error": f"{type(exc).__name__}: {exc}"}
                )

        return SuiteResult(name=spec.name, results=results, errors=errors)

    async def run_suite_async(
        self,
        spec: SuiteSpec,
        concurrency: int = 4,
    ) -> SuiteResult:
        semaphore = asyncio.Semaphore(concurrency)
        runner = EvaluationRunner(baseline_path=spec.baseline, judge=self._judge)

        async def _evaluate(case_spec: SuiteCaseSpec) -> tuple[EvaluationResult | None, dict | None]:
            async with semaphore:
                try:
                    _, _, result = await asyncio.to_thread(
                        runner.run_from_files, case_spec.trace, case_spec.case
                    )
                    return result, None
                except Exception as exc:  # noqa: BLE001
                    return None, {
                        "trace": case_spec.trace,
                        "error": f"{type(exc).__name__}: {exc}",
                    }

        outcomes = await asyncio.gather(*(_evaluate(c) for c in spec.cases))

        results = [r for r, _ in outcomes if r is not None]
        errors = [e for _, e in outcomes if e is not None]
        return SuiteResult(name=spec.name, results=results, errors=errors)

    def run_suite_from_file(self, suite_path: str | Path, use_async: bool = False) -> SuiteResult:
        spec = load_suite(suite_path)
        if use_async:
            return asyncio.run(self.run_suite_async(spec))
        return self.run_suite(spec)


class TaskExecutor:
    """
    End-to-end runner: drive an agent against a task, capture the trace,
    evaluate it, and produce a certified RunReport with a reproducibility
    manifest.

    Pipeline:  TaskSpec -> Solver.solve() -> AgentRun -> evaluate -> RunReport
    """

    def __init__(self, judge: Judge | None = None, baseline_path: str | None = None) -> None:
        self._aggregator = NinjaScoreAggregator(baseline_path=baseline_path, judge=judge)

    def run(
        self,
        task: TaskSpec,
        solver: Solver,
        sandbox: Sandbox | None = None,
        seed: int | None = None,
    ) -> RunReport:
        if seed is not None:
            random.seed(seed)
            os.environ["PYTHONHASHSEED"] = str(seed)

        if sandbox is None and task.sandbox != "none":
            sandbox = make_sandbox(task.sandbox, image=task.sandbox_image)

        run = solver.solve(task, sandbox)

        # Ensure the run carries the task text for downstream scoring.
        if not run.task:
            run = run.model_copy(update={"task": task.prompt})

        result = self._aggregator.evaluate(run, task.eval_case)

        manifest = build_manifest(
            run=run,
            solver=getattr(solver, "name", "unknown"),
            sandbox=sandbox.name if sandbox else "none",
            seed=seed,
        )

        return RunReport(task_id=task.task_id, run=run, result=result, manifest=manifest)
