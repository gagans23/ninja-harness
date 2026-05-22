"""Tests for the grounding-metric judge hook (v1.0)."""

from __future__ import annotations

from ninja_harness.schemas import AgentRun, EvaluationCase
from ninja_harness.scoring.grounding import GroundingScorer
from ninja_harness.scoring.judge import DeterministicJudge


def _run(output: str) -> AgentRun:
    return AgentRun(agent_name="A", task="t", final_output=output)


def _case(refs: list[str]) -> EvaluationCase:
    return EvaluationCase(task="t", references=refs)


def test_default_is_deterministic_coverage() -> None:
    # No judge → existing keyword-coverage behavior (details has 'coverage').
    scorer = GroundingScorer()
    result = scorer.score(_run("tokyo population is large"), _case(["tokyo population data"]))
    assert "coverage" in result.details
    assert "judge" not in result.details


def test_judge_used_when_supplied_and_refs_exist() -> None:
    scorer = GroundingScorer(judge=DeterministicJudge())
    result = scorer.score(
        _run("flashattention reduces memory cost"),
        _case(["flashattention reduces attention memory cost"]),
    )
    assert result.details.get("judge") == "deterministic"
    assert 0.0 <= result.score <= 1.0


def test_judge_ignored_without_references() -> None:
    # No references → judge is not used; falls back to claim-marker logic.
    scorer = GroundingScorer(judge=DeterministicJudge())
    result = scorer.score(_run("a simple statement"), _case([]))
    assert "judge" not in result.details


def test_custom_judge_score_drives_grounding() -> None:
    class HalfJudge:
        name = "half"

        def compare(self, prediction: str, reference: str) -> tuple[float, dict]:
            return 0.5, {"why": "fixed"}

    scorer = GroundingScorer(judge=HalfJudge())
    result = scorer.score(_run("anything"), _case(["some reference text"]))
    assert result.score == 0.5
    assert result.details["judge"] == "half"
