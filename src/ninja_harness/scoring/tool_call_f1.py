"""Tool Call F1 — precision / recall / F1 over expected vs actual tool calls."""

from __future__ import annotations

import json
from typing import Any, Optional

from ninja_harness.schemas import AgentRun, EvaluationCase, MetricResult, ToolCall
from ninja_harness.scoring.base import BaseScorer

_PASS_THRESHOLD = 0.6


def _normalize_args(args: dict[str, Any]) -> str:
    """Stable JSON string for argument comparison (sorted keys, lowercased values)."""
    def _lower(v: Any) -> Any:
        if isinstance(v, str):
            return v.lower().strip()
        if isinstance(v, dict):
            return {k: _lower(vv) for k, vv in v.items()}
        if isinstance(v, list):
            return [_lower(i) for i in v]
        return v

    return json.dumps(_lower(args), sort_keys=True)


def _call_key(tc: ToolCall) -> str:
    return f"{tc.tool_name.lower()}::{_normalize_args(tc.arguments)}"


def _fuzzy_name_match(a: str, b: str) -> bool:
    return a.lower().strip() == b.lower().strip()


class ToolCallF1Scorer(BaseScorer):
    """
    Compares actual tool calls against the expected tool calls in the eval case.

    Matching strategy:
    1. Exact match: same tool_name + normalized arguments.
    2. Name-only match (partial credit): same tool_name, different arguments.
    """

    @property
    def name(self) -> str:
        return "tool_call_f1"

    def score(
        self,
        run: AgentRun,
        case: Optional[EvaluationCase] = None,
    ) -> MetricResult:
        if not case or not case.expected_tool_calls:
            return self._not_applicable(
                "No expected_tool_calls in eval case; skipping Tool Call F1."
            )

        actual = run.tool_calls
        expected = case.expected_tool_calls

        actual_keys = [_call_key(tc) for tc in actual]
        expected_keys = [_call_key(tc) for tc in expected]

        # Exact matches
        actual_set = set(actual_keys)
        expected_set = set(expected_keys)
        true_positives_exact = actual_set & expected_set

        # Name-only partial matches (for calls not exactly matched)
        unmatched_actual = [
            tc for tc in actual if _call_key(tc) not in true_positives_exact
        ]
        unmatched_expected = [
            tc for tc in expected if _call_key(tc) not in true_positives_exact
        ]

        partial_matches: list[tuple[str, str]] = []
        used_expected: set[int] = set()
        for atc in unmatched_actual:
            for i, etc in enumerate(unmatched_expected):
                if i not in used_expected and _fuzzy_name_match(atc.tool_name, etc.tool_name):
                    partial_matches.append((atc.tool_name, etc.tool_name))
                    used_expected.add(i)
                    break

        # Counts (partial matches count as 0.5)
        tp = len(true_positives_exact) + 0.5 * len(partial_matches)
        fp = len(actual) - len(true_positives_exact) - len(partial_matches)
        fn = len(expected) - len(true_positives_exact) - len(partial_matches)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        passed = f1 >= _PASS_THRESHOLD
        failure_reasons = []
        recommendations = []

        false_negative_names = [
            tc.tool_name for tc in expected
            if _call_key(tc) not in true_positives_exact
            and tc.tool_name not in [m[1] for m in partial_matches]
        ]
        false_positive_names = [
            tc.tool_name for tc in actual
            if _call_key(tc) not in true_positives_exact
            and tc.tool_name not in [m[0] for m in partial_matches]
        ]

        if false_negative_names:
            failure_reasons.append(
                f"Missing expected tool calls: {', '.join(false_negative_names[:5])}"
            )
            recommendations.append("Verify agent invokes all required tools for this task.")
        if false_positive_names:
            failure_reasons.append(
                f"Unexpected tool calls: {', '.join(false_positive_names[:5])}"
            )
            recommendations.append(
                "Check whether extra tool calls indicate unnecessary work or scope creep."
            )

        return MetricResult(
            name=self.name,
            score=round(f1, 4),
            passed=passed,
            details={
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "true_positives_exact": len(true_positives_exact),
                "partial_matches": len(partial_matches),
                "false_positives": max(0, int(fp)),
                "false_negatives": max(0, int(fn)),
                "actual_count": len(actual),
                "expected_count": len(expected),
            },
            failure_reasons=failure_reasons,
            recommendations=recommendations,
        )
