"""Tests for Handoff Integrity scorer."""

from __future__ import annotations

import pytest

from ninja_harness.schemas import AgentRun, Handoff
from ninja_harness.scoring.handoff_integrity import HandoffIntegrityScorer


def make_run_with_handoffs(*handoffs: Handoff) -> AgentRun:
    return AgentRun(
        agent_name="A",
        task="t",
        final_output="done",
        handoffs=list(handoffs),
    )


def perfect_handoff(**kwargs) -> Handoff:
    defaults = dict(
        source_agent="AgentA",
        target_agent="AgentB",
        reason="Needs specialised knowledge",
        context_summary="Researching transformer efficiency",
        expected_next_action="Run web_search for efficiency papers",
        task_id="task-001",
        trace_id="trace-001",
    )
    defaults.update(kwargs)
    return Handoff(**defaults)


@pytest.fixture
def scorer() -> HandoffIntegrityScorer:
    return HandoffIntegrityScorer()


def test_no_handoffs_is_not_applicable(scorer: HandoffIntegrityScorer) -> None:
    run = AgentRun(agent_name="A", task="t", final_output="out")
    result = scorer.score(run)
    assert result.score == -1.0


def test_perfect_handoff_scores_1(scorer: HandoffIntegrityScorer) -> None:
    run = make_run_with_handoffs(perfect_handoff())
    result = scorer.score(run)
    assert result.score == pytest.approx(1.0)
    assert result.passed is True


def test_missing_reason_penalises(scorer: HandoffIntegrityScorer) -> None:
    run = make_run_with_handoffs(perfect_handoff(reason=""))
    result = scorer.score(run)
    assert result.score < 1.0


def test_missing_context_penalises(scorer: HandoffIntegrityScorer) -> None:
    run = make_run_with_handoffs(perfect_handoff(context_summary=""))
    result = scorer.score(run)
    assert result.score < 1.0


def test_missing_ids_minor_penalty(scorer: HandoffIntegrityScorer) -> None:
    run = make_run_with_handoffs(perfect_handoff(task_id=None, trace_id=None))
    result = scorer.score(run)
    assert 0.9 < result.score < 1.0


def test_multiple_handoffs_averaged(scorer: HandoffIntegrityScorer) -> None:
    h_good = perfect_handoff()
    h_bad = perfect_handoff(reason="", context_summary="", expected_next_action="")
    run = make_run_with_handoffs(h_good, h_bad)
    result = scorer.score(run)
    assert 0.4 < result.score < 1.0


def test_failure_reasons_populated(scorer: HandoffIntegrityScorer) -> None:
    run = make_run_with_handoffs(perfect_handoff(reason=""))
    result = scorer.score(run)
    assert len(result.failure_reasons) > 0
