"""Tests for the suite runner (sync + async) and suite loading."""

from __future__ import annotations

import asyncio
from pathlib import Path

from ninja_harness.datasets.loader import load_suite
from ninja_harness.runner import SuiteRunner
from ninja_harness.schemas import SuiteCaseSpec, SuiteResult, SuiteSpec

SUITE = Path("src/ninja_harness/examples/example_suite.yaml")
EXAMPLES = Path("src/ninja_harness/examples")


def test_load_suite_resolves_paths() -> None:
    spec = load_suite(SUITE)
    assert isinstance(spec, SuiteSpec)
    assert len(spec.cases) == 7
    # Paths resolved to absolute
    for c in spec.cases:
        assert Path(c.trace).is_absolute()
        assert Path(c.trace).exists()


def test_run_suite_sync() -> None:
    runner = SuiteRunner()
    spec = load_suite(SUITE)
    result = runner.run_suite(spec)
    assert isinstance(result, SuiteResult)
    assert result.total == 7
    assert result.errors == []
    assert 0.0 <= result.pass_rate <= 1.0
    assert result.average_score > 0


def test_run_suite_async() -> None:
    runner = SuiteRunner()
    spec = load_suite(SUITE)
    result = asyncio.run(runner.run_suite_async(spec, concurrency=3))
    assert result.total == 7
    assert result.errors == []


def test_sync_and_async_agree_on_count() -> None:
    runner = SuiteRunner()
    spec = load_suite(SUITE)
    sync_result = runner.run_suite(spec)
    async_result = asyncio.run(runner.run_suite_async(spec))
    assert sync_result.total == async_result.total
    assert sync_result.passed == async_result.passed


def test_suite_collects_errors_not_aborts() -> None:
    spec = SuiteSpec(
        name="error-suite",
        cases=[
            SuiteCaseSpec(trace=str(EXAMPLES / "simple_agent_trace.json")),
            SuiteCaseSpec(trace="nonexistent_trace.json"),
        ],
    )
    runner = SuiteRunner()
    result = runner.run_suite(spec)
    assert result.total == 1  # one succeeded
    assert len(result.errors) == 1
    assert "nonexistent_trace.json" in result.errors[0]["trace"]


def test_suite_result_properties() -> None:
    runner = SuiteRunner()
    result = runner.run_suite(load_suite(SUITE))
    assert result.passed + result.warned + result.failed == result.total
