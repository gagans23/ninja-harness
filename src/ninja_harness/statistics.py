"""
Statistical reliability analysis for repeated agent evaluations.

Agents are stochastic. A single run's NARI score is a point estimate with
unknown variance — it can mislead. This module aggregates N repeated
evaluations of the same task into reliability statistics:

- mean / std / min / max of the NARI score
- 95% confidence interval on the mean (t-distribution approximation)
- pass@k:   probability at least one of k trials certifies PASS
- pass^k:   probability ALL k trials certify PASS (the reliability metric,
            following the tau-bench formulation)
- consistency: 1 - normalized standard deviation

These are computed empirically from the observed trials (no model assumptions
beyond the CI), so they are honest descriptions of the runs you actually ran.
"""

from __future__ import annotations

import math
from collections import Counter

from ninja_harness.schemas import (
    AggregateResult,
    EvaluationResult,
    ReliabilityStats,
)

# Two-sided 95% t-critical values for small samples (df = n-1).
# Falls back to the normal approximation (1.96) for larger samples.
_T95 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
    6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
    15: 2.131, 20: 2.086, 30: 2.042,
}


def _t_critical(n: int) -> float:
    df = n - 1
    if df <= 0:
        return 0.0
    if df in _T95:
        return _T95[df]
    # nearest tabulated df below, else normal approximation
    for key in sorted(_T95, reverse=True):
        if df >= key:
            return _T95[key] if df < 30 else 1.96
    return 1.96


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def stdev(values: list[float]) -> float:
    """Sample standard deviation (n-1 denominator)."""
    n = len(values)
    if n < 2:
        return 0.0
    mu = mean(values)
    var = sum((v - mu) ** 2 for v in values) / (n - 1)
    return math.sqrt(var)


def confidence_interval_95(values: list[float]) -> tuple[float, float]:
    """95% CI on the mean using a t-distribution approximation."""
    n = len(values)
    if n == 0:
        return 0.0, 0.0
    mu = mean(values)
    if n == 1:
        return mu, mu
    se = stdev(values) / math.sqrt(n)
    margin = _t_critical(n) * se
    return mu - margin, mu + margin


def pass_at_k(pass_flags: list[bool]) -> float:
    """
    Empirical pass@k: probability at least one of the k trials passed.
    With observed trials this is simply 1 if any passed, else 0 — but we
    report the observed pass *rate* as the estimator of single-trial success,
    and derive pass@k / pass^k from it for interpretability.
    """
    if not pass_flags:
        return 0.0
    return 1.0 if any(pass_flags) else 0.0


def pass_hat_k(pass_flags: list[bool]) -> float:
    """Empirical pass^k: 1 only if ALL k trials passed."""
    if not pass_flags:
        return 0.0
    return 1.0 if all(pass_flags) else 0.0


def estimated_pass_rate(pass_flags: list[bool]) -> float:
    """Single-trial pass probability estimated from observed trials."""
    if not pass_flags:
        return 0.0
    return sum(1 for p in pass_flags if p) / len(pass_flags)


def consistency(values: list[float], scale: float = 100.0) -> float:
    """1 - (std / scale), clamped to [0, 1]. Higher = more consistent."""
    if len(values) < 2:
        return 1.0
    return max(0.0, min(1.0, 1.0 - stdev(values) / scale))


def _verdict(stats: ReliabilityStats) -> tuple[str, list[str]]:
    notes: list[str] = []
    if stats.pass_hat_k >= 1.0 and stats.consistency >= 0.9:
        verdict = "RELIABLE"
        notes.append("All trials certified PASS with low score variance.")
    elif stats.pass_at_k >= 1.0 and stats.pass_hat_k < 1.0:
        verdict = "FLAKY"
        notes.append(
            "Agent passed in some trials but not all (pass@k=1, pass^k<1). "
            "This is the classic flaky-agent signature — investigate non-determinism."
        )
    elif stats.pass_at_k < 1.0:
        verdict = "UNRELIABLE"
        notes.append("Agent failed to certify PASS in every trial.")
    else:
        verdict = "UNKNOWN"
    if stats.consistency < 0.7:
        notes.append(
            f"High score variance (std={stats.std_score:.1f}); results are not "
            f"stable across runs. Increase trials or stabilize the agent."
        )
    return verdict, notes


def aggregate_results(
    results: list[EvaluationResult],
    task_label: str = "aggregate",
) -> AggregateResult:
    """
    Aggregate repeated EvaluationResults for the same task into an
    AggregateResult with reliability statistics.
    """
    if not results:
        raise ValueError("aggregate_results requires at least one EvaluationResult.")

    scores = [r.ninja_score for r in results]
    pass_flags = [r.certification == "PASS" for r in results]
    ci_low, ci_high = confidence_interval_95(scores)

    stats = ReliabilityStats(
        trials=len(results),
        mean_score=round(mean(scores), 2),
        std_score=round(stdev(scores), 2),
        min_score=round(min(scores), 2),
        max_score=round(max(scores), 2),
        ci_low=round(ci_low, 2),
        ci_high=round(ci_high, 2),
        pass_at_k=round(pass_at_k(pass_flags), 4),
        pass_hat_k=round(pass_hat_k(pass_flags), 4),
        consistency=round(consistency(scores), 4),
        certification_distribution=dict(Counter(r.certification for r in results)),
    )

    # Per-metric mean across trials (only applicable metrics)
    per_metric: dict[str, list[float]] = {}
    for r in results:
        for m in r.metric_results:
            if m.is_applicable:
                per_metric.setdefault(m.name, []).append(m.score)
    per_metric_mean = {k: round(mean(v), 4) for k, v in per_metric.items()}

    verdict, notes = _verdict(stats)
    notes.append(
        f"Estimated single-trial PASS rate: {estimated_pass_rate(pass_flags):.0%} "
        f"over {len(results)} trial(s)."
    )

    return AggregateResult(
        task_label=task_label,
        reliability=stats,
        run_ids=[r.run_id for r in results],
        per_metric_mean=per_metric_mean,
        verdict=verdict,
        notes=notes,
    )
