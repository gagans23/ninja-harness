"""
pytest plugin — assert agent quality inside your pytest suite.

Enabled automatically via the `pytest11` entry point (see pyproject). Provides a
`ninja_eval` fixture exposing `evaluate` and `assert_agent`:

    def test_billing_agent(ninja_eval):
        result = ninja_eval.evaluate("traces/billing.json", "cases/billing.yaml")
        assert result.certification == "PASS"

    def test_research_agent(ninja_eval):
        ninja_eval.assert_agent("traces/research.json", "cases/research.yaml",
                                min_score=80, min_safety=0.8)

Nothing here makes network calls; scoring is deterministic by default.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from ninja_harness.testing import assert_agent, evaluate_trace


@dataclass
class NinjaEval:
    """Thin handle exposing the Ninja Harness test helpers as methods."""

    evaluate = staticmethod(evaluate_trace)
    assert_agent = staticmethod(assert_agent)


@pytest.fixture
def ninja_eval() -> NinjaEval:
    """Fixture providing `.evaluate(...)` and `.assert_agent(...)`."""
    return NinjaEval()
