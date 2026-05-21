"""
Output Hygiene metric.

Many agents reach the right answer but bury it in noise — raw logs, stack
traces, environment/deprecation warnings, dumped headlines, ANSI escape codes,
or hundreds of lines of intermediate output. The final answer should be a
concise, evidence-based summary; raw material belongs in artifacts, not in the
user-facing answer.

This metric measures the signal-to-noise of `final_output`. It is deterministic
(regex/heuristic based) and is **reported separately** — it is not part of the
weighted Ninja Agent Reliability Index by default, so adding it does not change
existing composite scores. It exists to catch exactly the "output too noisy"
failure mode and to recommend separating the answer from logs.
"""

from __future__ import annotations

import re

from ninja_harness.schemas import AgentRun, EvaluationCase, MetricResult
from ninja_harness.scoring.base import BaseScorer

# Noise signals and their per-occurrence penalty (capped).
_LOG_LEVEL = re.compile(r"\b(ERROR|WARNING|WARN|DEBUG|CRITICAL|TRACEBACK)\b", re.IGNORECASE)
_TRACEBACK = re.compile(r"Traceback \(most recent call last\)|File \".*\", line \d+")
_WARNING_LINE = re.compile(r"\b\w*Warning\b\s*:")  # DeprecationWarning:, UserWarning:
_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_TIMESTAMP = re.compile(r"\b\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}\b")
_URL = re.compile(r"https?://\S+")

_LONG_OUTPUT_CHARS = 1500       # answers longer than this start losing points
_VERY_LONG_OUTPUT_CHARS = 4000


def _count(pattern: re.Pattern[str], text: str) -> int:
    return len(pattern.findall(text))


class OutputHygieneScorer(BaseScorer):
    """Scores how concise and noise-free the final answer is (0-1)."""

    @property
    def name(self) -> str:
        return "output_hygiene"

    def score(
        self,
        run: AgentRun,
        case: EvaluationCase | None = None,
    ) -> MetricResult:
        text = run.final_output or ""
        if not text.strip():
            return self._not_applicable("Empty final_output; nothing to assess.")

        lines = text.splitlines()
        n_lines = len(lines)

        signals: dict[str, int] = {
            "log_levels": _count(_LOG_LEVEL, text),
            "tracebacks": _count(_TRACEBACK, text),
            "warning_lines": _count(_WARNING_LINE, text),
            "ansi_codes": _count(_ANSI, text),
            "timestamps": _count(_TIMESTAMP, text),
            "urls": _count(_URL, text),
        }

        # Duplicate lines (after stripping) — a common log/dump signature.
        stripped = [ln.strip() for ln in lines if ln.strip()]
        duplicate_lines = len(stripped) - len(set(stripped))
        signals["duplicate_lines"] = duplicate_lines

        # Build a penalty in [0, 1].
        penalty = 0.0
        penalty += min(signals["log_levels"], 5) * 0.06
        penalty += min(signals["tracebacks"], 3) * 0.20
        penalty += min(signals["warning_lines"], 5) * 0.08
        penalty += 0.15 if signals["ansi_codes"] else 0.0
        penalty += min(signals["timestamps"], 5) * 0.04
        # Bulk URLs (raw link dumps) — a few links are fine.
        penalty += max(0, signals["urls"] - 2) * 0.03
        penalty += min(duplicate_lines, 10) * 0.03

        # Length penalty (verbosity).
        if len(text) > _VERY_LONG_OUTPUT_CHARS:
            penalty += 0.30
        elif len(text) > _LONG_OUTPUT_CHARS:
            penalty += 0.15

        score = max(0.0, min(1.0, 1.0 - penalty))
        passed = score >= 0.7

        failure_reasons: list[str] = []
        recommendations: list[str] = []
        if not passed:
            noisy = [k for k, v in signals.items() if v]
            failure_reasons.append(
                f"Final answer looks noisy (hygiene={score:.2f}). Detected: "
                f"{', '.join(noisy) or 'excessive length'}."
            )
            recommendations.append(
                "Separate the answer from the logs: return a concise, evidence-based "
                "summary and move raw headlines/logs/warnings into artifacts (e.g. a "
                "saved report or the trace steps), not the final answer."
            )

        return MetricResult(
            name=self.name,
            score=round(score, 4),
            passed=passed,
            details={
                "signals": signals,
                "char_length": len(text),
                "line_count": n_lines,
                "weighted_in_composite": False,
            },
            failure_reasons=failure_reasons,
            recommendations=recommendations,
        )
