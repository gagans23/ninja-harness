"""Tests for the test helpers (assert_agent / evaluate_trace) and pytest plugin.

The `ninja_eval` fixture is provided by ninja_harness.pytest_plugin via the
pytest11 entry point, so it's available here once the package is installed.
"""

from __future__ import annotations

import pytest

from ninja_harness.testing import assert_agent, evaluate_trace

GOOD_TRACE = {
    "agent_name": "A", "task": "summarize",
    "final_output": "transformers improved efficiency via flashattention and moe",
}
CASE = {"case_id": "c", "task": "summarize",
        "expected_output": "transformers improved efficiency via flashattention and moe"}


def test_evaluate_trace_dict() -> None:
    result = evaluate_trace(GOOD_TRACE, None)
    assert result.ninja_score >= 0


def test_assert_agent_passes() -> None:
    # high goal match + safe → should clear a modest bar
    result = assert_agent(GOOD_TRACE, None, min_safety=0.8)
    assert result.metric_by_name("safety").score == 1.0


def test_assert_agent_raises_on_low_score() -> None:
    # Mismatched expected output → low goal success → score below a high bar.
    bad_trace = {"agent_name": "A", "task": "t", "final_output": "completely unrelated answer"}
    bad_case = {"case_id": "c", "task": "t",
                "expected_output": "the mitochondria is the powerhouse of the cell"}
    with pytest.raises(AssertionError, match="score"):
        assert_agent(bad_trace, bad_case, min_score=99)


def test_assert_agent_certification_floor() -> None:
    leak = {"agent_name": "A", "task": "t",
            "final_output": "the key is sk-AAAABBBBCCCCDDDDEEEEFFFF1234567890abcd"}
    with pytest.raises(AssertionError):
        assert_agent(leak, None, certification="PASS")


def test_pytest_plugin_fixture_available(ninja_eval) -> None:
    # `ninja_eval` comes from the installed plugin's entry point.
    result = ninja_eval.evaluate(GOOD_TRACE, None)
    assert result.run_id
    ninja_eval.assert_agent(GOOD_TRACE, None, min_safety=0.8)
