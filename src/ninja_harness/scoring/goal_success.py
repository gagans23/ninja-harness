"""Goal Success Score — deterministic token-overlap implementation for v0.1."""

from __future__ import annotations

import re
from typing import Optional

from ninja_harness.schemas import AgentRun, EvaluationCase, MetricResult
from ninja_harness.scoring.base import BaseScorer

_PASS_THRESHOLD = 0.5


def _tokenize(text: str) -> set[str]:
    """Lowercase, strip punctuation, return set of words (length >= 2)."""
    tokens = re.findall(r"\b[a-z]{2,}\b", text.lower())
    return set(tokens)


class GoalSuccessScorer(BaseScorer):
    """
    Measures how well the agent's final output matches the expected output.

    v0.1: deterministic token-overlap (Jaccard similarity over word sets).
    The architecture is designed so an LLM-as-judge can replace or supplement
    this calculation in v0.2 without changing the scorer interface.
    """

    @property
    def name(self) -> str:
        return "goal_success"

    def score(
        self,
        run: AgentRun,
        case: Optional[EvaluationCase] = None,
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

        actual_tokens = _tokenize(run.final_output)
        expected_tokens = _tokenize(expected)

        if not expected_tokens:
            return self._not_applicable("expected_output contains no scoreable tokens.")

        intersection = actual_tokens & expected_tokens
        union = actual_tokens | expected_tokens
        jaccard = len(intersection) / len(union) if union else 0.0

        # Also compute recall (coverage of expected tokens).
        recall = len(intersection) / len(expected_tokens)

        # Blend jaccard + recall; recall is more important for correctness.
        blended = 0.4 * jaccard + 0.6 * recall

        passed = blended >= _PASS_THRESHOLD
        failure_reasons = []
        recommendations = []

        if not passed:
            missing = expected_tokens - actual_tokens
            top_missing = sorted(missing)[:5]
            failure_reasons.append(
                f"Output covers only {recall:.0%} of expected key terms. "
                f"Missing: {', '.join(top_missing)}"
            )
            recommendations.append(
                "Review whether the agent's final answer addresses all required topics. "
                "Consider adding an LLM-as-judge check for semantic similarity (v0.2)."
            )

        return MetricResult(
            name=self.name,
            score=round(blended, 4),
            passed=passed,
            details={
                "jaccard": round(jaccard, 4),
                "recall": round(recall, 4),
                "blended": round(blended, 4),
                "actual_token_count": len(actual_tokens),
                "expected_token_count": len(expected_tokens),
                "matching_tokens": len(intersection),
            },
            failure_reasons=failure_reasons,
            recommendations=recommendations,
        )
