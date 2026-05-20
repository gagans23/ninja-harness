"""Goal Success Score — deterministic by default, judge-pluggable in v0.2."""

from __future__ import annotations

import re

from ninja_harness.schemas import AgentRun, EvaluationCase, MetricResult
from ninja_harness.scoring.base import BaseScorer
from ninja_harness.scoring.judge import DeterministicJudge, Judge

_PASS_THRESHOLD = 0.5


def _tokenize(text: str) -> set[str]:
    """Lowercase, strip punctuation, return set of words (length >= 2)."""
    tokens = re.findall(r"\b[a-z]{2,}\b", text.lower())
    return set(tokens)


class GoalSuccessScorer(BaseScorer):
    """
    Measures how well the agent's final output matches the expected output.

    The comparison is delegated to a Judge (see scoring/judge.py). The default
    is DeterministicJudge (token-overlap), which keeps scoring reproducible and
    free of external calls. Pass a different judge — including a custom
    LLM-as-judge — to change the comparison strategy:

        scorer = GoalSuccessScorer(judge=EmbeddingJudge())
        scorer = GoalSuccessScorer(judge=MyLLMJudge())
    """

    def __init__(self, judge: Judge | None = None) -> None:
        self._judge: Judge = judge or DeterministicJudge()

    @property
    def name(self) -> str:
        return "goal_success"

    def score(
        self,
        run: AgentRun,
        case: EvaluationCase | None = None,
    ) -> MetricResult:
        expected = None
        if case and case.expected_output:
            expected = case.expected_output
        elif run.expected_output:
            expected = run.expected_output

        if not expected:
            return self._not_applicable(
                "No expected_output provided; skipping goal success scoring."
            )

        if not _tokenize(expected):
            return self._not_applicable("expected_output contains no scoreable tokens.")

        score, details = self._judge.compare(run.final_output, expected)
        passed = score >= _PASS_THRESHOLD

        failure_reasons = []
        recommendations = []
        if not passed:
            expected_tokens = _tokenize(expected)
            actual_tokens = _tokenize(run.final_output)
            missing = sorted(expected_tokens - actual_tokens)[:5]
            failure_reasons.append(
                f"Output diverges from expected answer (judge='{self._judge.name}', "
                f"score={score:.2f}). Missing key terms: {', '.join(missing)}"
            )
            recommendations.append(
                "Review whether the agent's final answer addresses all required topics. "
                "For semantic matching, try GoalSuccessScorer(judge=EmbeddingJudge())."
            )

        return MetricResult(
            name=self.name,
            score=score,
            passed=passed,
            details=details,
            failure_reasons=failure_reasons,
            recommendations=recommendations,
        )
