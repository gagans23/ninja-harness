"""Tests for benchmark dataset loaders."""

from __future__ import annotations

import pytest

from ninja_harness.datasets import load_benchmark
from ninja_harness.datasets.benchmarks import load_gaia, load_swebench, load_taubench
from ninja_harness.schemas import EvaluationCase

SWE = "examples/benchmarks/swebench_sample.jsonl"
GAIA = "examples/benchmarks/gaia_sample.jsonl"
TAU = "examples/benchmarks/taubench_sample.json"


def test_load_swebench() -> None:
    cases = load_swebench(SWE)
    assert len(cases) == 2
    assert all(isinstance(c, EvaluationCase) for c in cases)
    assert cases[0].case_id == "demo__repo-001"
    assert "off-by-one" in cases[0].task
    assert cases[0].metadata["benchmark"] == "swebench"
    assert cases[0].metadata["repo"] == "demo/repo"


def test_load_gaia() -> None:
    cases = load_gaia(GAIA)
    assert len(cases) == 2
    assert cases[0].expected_output == "Montevideo"
    assert cases[0].metadata["level"] == 1


def test_load_taubench() -> None:
    cases = load_taubench(TAU)
    assert len(cases) == 2
    c = cases[0]
    assert len(c.expected_tool_calls) == 2
    assert c.expected_tool_calls[0].tool_name == "lookup_charges"
    assert c.expected_tool_calls[1].arguments["amount"] == 20.0
    assert c.references  # outputs mapped to references


def test_load_benchmark_dispatch() -> None:
    assert len(load_benchmark("swebench", SWE)) == 2
    assert len(load_benchmark("gaia", GAIA)) == 2
    assert len(load_benchmark("tau-bench", TAU)) == 2


def test_load_benchmark_unknown() -> None:
    with pytest.raises(ValueError):
        load_benchmark("nope", SWE)


def test_missing_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_swebench("does_not_exist.jsonl")


def test_benchmark_cases_are_evaluable() -> None:
    """A loaded case should drive the normal evaluation pipeline."""
    from ninja_harness.schemas import AgentRun
    from ninja_harness.scoring.ninja_score import NinjaScoreAggregator

    case = load_gaia(GAIA)[0]
    run = AgentRun(agent_name="A", task=case.task, final_output="The capital is Montevideo.")
    result = NinjaScoreAggregator().evaluate(run, case)
    assert 0 <= result.ninja_score <= 100
