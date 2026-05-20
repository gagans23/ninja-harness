"""Grounding Score — checks whether final output is supported by references."""

from __future__ import annotations

import re

from ninja_harness.schemas import AgentRun, EvaluationCase, MetricResult
from ninja_harness.scoring.base import BaseScorer

_PASS_THRESHOLD = 0.5

# Patterns that look like unsupported factual claims when no references exist.
_CLAIM_PATTERNS = [
    r"\b(studies show|research shows|it is known|it is proven|according to experts)\b",
    r"\b(always|never|all|none|every|no one)\b",
    r"\b\d{4}\b",  # years — plausible citation targets
]


def _tokenize_reference(text: str) -> set[str]:
    return set(re.findall(r"\b[a-z]{3,}\b", text.lower()))


def _count_claim_markers(text: str) -> int:
    count = 0
    for pattern in _CLAIM_PATTERNS:
        count += len(re.findall(pattern, text.lower()))
    return count


class GroundingScorer(BaseScorer):
    """
    Measures how well the final output is grounded in provided reference documents.

    v0.1: deterministic keyword-coverage approach.
    - If references are provided: score = fraction of output key terms that appear
      in at least one reference document.
    - If no references: penalise outputs that contain claim markers (e.g. "studies
      show", absolute quantifiers) without supporting documents.

    Designed for RAGAS / LLM-judge integration in v0.2 without interface changes.
    """

    @property
    def name(self) -> str:
        return "grounding"

    def score(
        self,
        run: AgentRun,
        case: EvaluationCase | None = None,
    ) -> MetricResult:
        references: list[str] = []
        if case and case.references:
            references = case.references

        output_tokens = _tokenize_reference(run.final_output)

        if not output_tokens:
            return self._not_applicable("Final output contains no scoreable tokens.")

        if not references:
            claim_count = _count_claim_markers(run.final_output)
            if claim_count == 0:
                return MetricResult(
                    name=self.name,
                    score=0.7,  # neutral — no references, no strong claims
                    passed=True,
                    details={
                        "references_provided": False,
                        "claim_markers_found": 0,
                        "note": "No references provided; output contains no strong factual claims.",
                    },
                )
            penalty = min(1.0, claim_count * 0.1)
            adjusted = max(0.0, 0.7 - penalty)
            return MetricResult(
                name=self.name,
                score=round(adjusted, 4),
                passed=adjusted >= _PASS_THRESHOLD,
                details={
                    "references_provided": False,
                    "claim_markers_found": claim_count,
                    "note": (
                        "Output contains factual-looking claim markers but no references "
                        "were provided to verify them."
                    ),
                },
                failure_reasons=[
                    f"Found {claim_count} unsupported claim marker(s) with no reference documents."
                ],
                recommendations=[
                    "Provide reference documents in the eval case so grounding can be verified.",
                    "If the agent cites facts, ensure those claims appear in the provided context.",
                ],
            )

        # Build combined reference token set
        ref_tokens: set[str] = set()
        for ref in references:
            ref_tokens |= _tokenize_reference(ref)

        covered = output_tokens & ref_tokens
        coverage = len(covered) / len(output_tokens) if output_tokens else 0.0

        passed = coverage >= _PASS_THRESHOLD
        failure_reasons = []
        recommendations = []

        if not passed:
            uncovered_sample = sorted(output_tokens - ref_tokens)[:8]
            failure_reasons.append(
                f"Only {coverage:.0%} of output tokens appear in references. "
                f"Unsupported terms: {', '.join(uncovered_sample)}"
            )
            recommendations.append(
                "Ensure the agent draws from the provided reference documents. "
                "Consider adding RAGAS or an LLM-as-judge grounding check (v0.2)."
            )

        return MetricResult(
            name=self.name,
            score=round(coverage, 4),
            passed=passed,
            details={
                "references_provided": True,
                "reference_count": len(references),
                "output_token_count": len(output_tokens),
                "covered_token_count": len(covered),
                "coverage": round(coverage, 4),
            },
            failure_reasons=failure_reasons,
            recommendations=recommendations,
        )
