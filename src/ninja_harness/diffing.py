"""
Diff two evaluation results.

Compares a baseline EvaluationResult against a current one — per-metric deltas,
the NARI score change, and whether certification moved — so you can review
exactly what improved or regressed between two runs (e.g. in a PR).
"""

from __future__ import annotations

from ninja_harness.schemas import DiffReport, EvaluationResult, MetricDelta


def _applicable_score(result: EvaluationResult, name: str) -> float | None:
    m = result.metric_by_name(name)
    if m is None or not m.is_applicable:
        return None
    return m.score


def diff_results(
    baseline: EvaluationResult,
    current: EvaluationResult,
    tolerance: float = 0.01,
) -> DiffReport:
    """Build a DiffReport comparing *current* against *baseline*."""
    names: list[str] = []
    for m in baseline.metric_results + current.metric_results:
        if m.name not in names:
            names.append(m.name)

    deltas: list[MetricDelta] = []
    regressions: list[str] = []
    improvements: list[str] = []

    for name in names:
        b = _applicable_score(baseline, name)
        c = _applicable_score(current, name)

        if b is None and c is None:
            status, delta = "na", None
        elif b is None:
            status, delta = "added", None
        elif c is None:
            status, delta = "removed", None
        else:
            delta = round(c - b, 4)
            if delta > tolerance:
                status = "improved"
                improvements.append(name)
            elif delta < -tolerance:
                status = "regressed"
                regressions.append(name)
            else:
                status = "unchanged"

        deltas.append(MetricDelta(
            name=name, baseline_score=b, current_score=c, delta=delta, status=status,
        ))

    return DiffReport(
        baseline_run_id=baseline.run_id,
        current_run_id=current.run_id,
        baseline_score=baseline.ninja_score,
        current_score=current.ninja_score,
        score_delta=round(current.ninja_score - baseline.ninja_score, 2),
        baseline_certification=baseline.certification,
        current_certification=current.certification,
        certification_changed=baseline.certification != current.certification,
        metric_deltas=deltas,
        regressions=regressions,
        improvements=improvements,
    )
