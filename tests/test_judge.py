"""Tests for the judge plug-in interface."""

from __future__ import annotations

import pytest

from ninja_harness.schemas import AgentRun, EvaluationCase
from ninja_harness.scoring.goal_success import GoalSuccessScorer
from ninja_harness.scoring.judge import (
    DeterministicJudge,
    EmbeddingJudge,
    EnsembleJudge,
    Judge,
    PositionSwapJudge,
    RubricJudge,
)


def test_deterministic_judge_is_a_judge() -> None:
    assert isinstance(DeterministicJudge(), Judge)


def test_deterministic_judge_perfect_match() -> None:
    judge = DeterministicJudge()
    score, details = judge.compare("the quick brown fox", "the quick brown fox")
    assert score == pytest.approx(1.0)
    assert details["recall"] == pytest.approx(1.0)


def test_deterministic_judge_no_overlap() -> None:
    judge = DeterministicJudge()
    score, _ = judge.compare("alpha beta gamma", "delta epsilon zeta")
    assert score == pytest.approx(0.0)


def test_deterministic_judge_empty_reference() -> None:
    judge = DeterministicJudge()
    score, details = judge.compare("anything", "")
    assert score == 0.0
    assert "reason" in details


def test_goal_success_uses_default_judge() -> None:
    scorer = GoalSuccessScorer()
    run = AgentRun(agent_name="A", task="t", final_output="transformers improved efficiency")
    case = EvaluationCase(task="t", expected_output="transformers improved efficiency")
    result = scorer.score(run, case)
    assert result.score == pytest.approx(1.0)
    assert result.details["judge"] == "deterministic"


def test_goal_success_custom_judge_injected() -> None:
    class AlwaysPerfect:
        name = "fake"

        def compare(self, prediction: str, reference: str) -> tuple[float, dict]:
            return 1.0, {"judge": self.name}

    scorer = GoalSuccessScorer(judge=AlwaysPerfect())
    run = AgentRun(agent_name="A", task="t", final_output="totally unrelated")
    case = EvaluationCase(task="t", expected_output="something else entirely")
    result = scorer.score(run, case)
    assert result.score == 1.0
    assert result.details["judge"] == "fake"


def test_goal_success_not_applicable_without_expected() -> None:
    scorer = GoalSuccessScorer()
    run = AgentRun(agent_name="A", task="t", final_output="out")
    result = scorer.score(run, None)
    assert result.score == -1.0


def test_embedding_judge_raises_without_dependency() -> None:
    """EmbeddingJudge must fail clearly if sentence-transformers is absent."""
    judge = EmbeddingJudge()
    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        with pytest.raises(ImportError, match="sentence-transformers"):
            judge.compare("a", "b")
    else:
        pytest.skip("sentence-transformers is installed; skipping absence test.")


# --------------------------------------------------------------------------
# Judge combinators (v0.3)
# --------------------------------------------------------------------------

def test_rubric_judge_is_a_judge() -> None:
    assert isinstance(RubricJudge(), Judge)


def test_rubric_judge_breakdown() -> None:
    judge = RubricJudge(rubric=[("relevance", 0.7), ("completeness", 0.3)])
    score, details = judge.compare("the quick brown fox", "the quick brown fox")
    assert score == pytest.approx(1.0)
    assert set(details["criteria"].keys()) == {"relevance", "completeness"}


def test_position_swap_averages_orderings() -> None:
    judge = PositionSwapJudge(DeterministicJudge())
    score, details = judge.compare("alpha beta", "alpha beta gamma")
    assert details["judge"] == "position_swap"
    assert "position_bias_delta" in details
    assert 0.0 <= score <= 1.0


def test_ensemble_mean() -> None:
    class Half:
        name = "half"
        def compare(self, p: str, r: str) -> tuple[float, dict]:
            return 0.5, {}

    class One:
        name = "one"
        def compare(self, p: str, r: str) -> tuple[float, dict]:
            return 1.0, {}

    judge = EnsembleJudge([Half(), One()])
    score, details = judge.compare("x", "y")
    assert score == pytest.approx(0.75)
    assert details["disagreement"] == pytest.approx(0.5)


def test_ensemble_requires_judges() -> None:
    with pytest.raises(ValueError):
        EnsembleJudge([])


def test_ensemble_min_aggregate() -> None:
    class Half:
        name = "half"
        def compare(self, p: str, r: str) -> tuple[float, dict]:
            return 0.5, {}

    class One:
        name = "one"
        def compare(self, p: str, r: str) -> tuple[float, dict]:
            return 1.0, {}

    judge = EnsembleJudge([Half(), One()], aggregate="min")
    score, _ = judge.compare("x", "y")
    assert score == pytest.approx(0.5)


def test_goal_success_with_ensemble_judge() -> None:
    scorer = GoalSuccessScorer(judge=EnsembleJudge([DeterministicJudge(), DeterministicJudge()]))
    run = AgentRun(agent_name="A", task="t", final_output="transformers improved")
    case = EvaluationCase(task="t", expected_output="transformers improved")
    result = scorer.score(run, case)
    assert result.score == pytest.approx(1.0)
    assert result.details["judge"] == "ensemble"
