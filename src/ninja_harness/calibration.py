"""
Judge calibration: measure agreement between automated judges and humans.

Automated judges drift and carry biases, so they must be checked against a
human-labeled set periodically. This module computes agreement statistics
between judge scores and human labels:

- mean absolute error
- agreement within a tolerance band
- Pearson correlation (linear)
- Spearman correlation (rank)
- Cohen's kappa (binary pass/fail at a 0.5 threshold)

All statistics are pure-Python and deterministic. If correlation/agreement is
low, recalibrate the judge or swap it (see scoring/judge.py).
"""

from __future__ import annotations

from ninja_harness.schemas import (
    CalibrationReport,
    EvaluationResult,
    HumanLabel,
)


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    mx, my = _mean(xs), _mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx == 0 or vy == 0:
        return None
    return cov / (vx**0.5 * vy**0.5)


def _ranks(values: list[float]) -> list[float]:
    """Average ranks (ties get the mean of their positions)."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg_rank = (i + j) / 2 + 1  # 1-based
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    return ranks


def _spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2:
        return None
    return _pearson(_ranks(xs), _ranks(ys))


def _cohen_kappa(judge: list[float], human: list[float], threshold: float = 0.5) -> float | None:
    """Cohen's kappa on binary pass/fail (score >= threshold)."""
    n = len(judge)
    if n == 0:
        return None
    jb = [s >= threshold for s in judge]
    hb = [s >= threshold for s in human]
    po = sum(1 for a, b in zip(jb, hb) if a == b) / n
    pj = sum(jb) / n
    ph = sum(hb) / n
    pe = pj * ph + (1 - pj) * (1 - ph)
    if pe == 1.0:
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1 - pe)


def calibrate(
    pairs: list[tuple[float, float]],
    metric: str = "overall",
    tolerance: float = 0.1,
) -> CalibrationReport:
    """Build a CalibrationReport from (judge_score, human_score) pairs."""
    if not pairs:
        raise ValueError("calibrate requires at least one (judge, human) pair.")

    judge = [p[0] for p in pairs]
    human = [p[1] for p in pairs]

    mae = _mean([abs(j - h) for j, h in pairs])
    within = sum(1 for j, h in pairs if abs(j - h) <= tolerance) / len(pairs)

    notes: list[str] = []
    pearson = _pearson(judge, human)
    spearman = _spearman(judge, human)
    kappa = _cohen_kappa(judge, human)

    if pearson is not None and pearson < 0.5:
        notes.append("Low linear correlation with humans (<0.5) — consider recalibrating the judge.")
    if mae > 0.25:
        notes.append("High mean absolute error (>0.25) — judge scores diverge substantially from humans.")
    if len(pairs) < 20:
        notes.append("Small sample (<20 pairs); treat correlation estimates as noisy.")

    return CalibrationReport(
        n=len(pairs),
        metric=metric,
        mean_abs_error=round(mae, 4),
        agreement_within_tolerance=round(within, 4),
        tolerance=tolerance,
        pearson=round(pearson, 4) if pearson is not None else None,
        spearman=round(spearman, 4) if spearman is not None else None,
        cohen_kappa=round(kappa, 4) if kappa is not None else None,
        notes=notes,
    )


def calibrate_from_results(
    results: list[EvaluationResult],
    labels: list[HumanLabel],
    metric: str = "goal_success",
    tolerance: float = 0.1,
) -> CalibrationReport:
    """
    Match human labels to judge scores by run_id (for the given metric) and
    compute a CalibrationReport. Labels with a different metric, or with no
    matching applicable judge score, are skipped.
    """
    by_run = {r.run_id: r for r in results}
    pairs: list[tuple[float, float]] = []
    for label in labels:
        if label.metric != metric:
            continue
        result = by_run.get(label.run_id)
        if result is None:
            continue
        mr = result.metric_by_name(metric)
        if mr is None or not mr.is_applicable:
            continue
        pairs.append((mr.score, label.human_score))

    if not pairs:
        raise ValueError(
            f"No matching (judge, human) pairs found for metric {metric!r}. "
            "Check that run_ids and metric names align between results and labels."
        )
    return calibrate(pairs, metric=metric, tolerance=tolerance)
