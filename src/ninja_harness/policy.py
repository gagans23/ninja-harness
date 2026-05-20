"""
Evaluation policy gating.

Lets teams define their own acceptance criteria (per-metric minimums, overall
score floors, max regression vs baseline) and apply them as a CI gate. This is
the "eval-driven development" pattern: gate merges on evaluation thresholds.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from ninja_harness.schemas import (
    EvaluationPolicy,
    EvaluationResult,
    GateResult,
    GateViolation,
)

_CERT_RANK = {"FAIL": 0, "WARN": 1, "PASS": 2}


def load_policy(path: str | Path) -> EvaluationPolicy:
    """Load an EvaluationPolicy from a YAML or JSON file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Policy file not found: {p}")
    with p.open() as f:
        if p.suffix.lower() in {".yaml", ".yml"}:
            raw = yaml.safe_load(f)
        elif p.suffix.lower() == ".json":
            raw = json.load(f)
        else:
            raise ValueError(f"Policy files must be YAML or JSON, got: {p.suffix}")
    return EvaluationPolicy.model_validate(raw)


def apply_policy(
    result: EvaluationResult,
    policy: EvaluationPolicy,
    baseline: EvaluationResult | None = None,
    redteam_findings: list[dict] | None = None,
) -> GateResult:
    """Evaluate *result* against *policy*, returning a GateResult."""
    violations: list[GateViolation] = []

    if policy.min_ninja_score is not None and result.ninja_score < policy.min_ninja_score:
        violations.append(
            GateViolation(
                rule="min_ninja_score",
                detail=f"Score {result.ninja_score:.1f} < required {policy.min_ninja_score:.1f}",
            )
        )

    if policy.min_safety_score is not None:
        safety = result.metric_by_name("safety")
        safety_score = safety.score if safety and safety.is_applicable else 1.0
        if safety_score < policy.min_safety_score:
            violations.append(
                GateViolation(
                    rule="min_safety_score",
                    detail=f"Safety {safety_score:.2f} < required {policy.min_safety_score:.2f}",
                )
            )

    if policy.required_certification is not None:
        have = _CERT_RANK.get(result.certification, 0)
        need = _CERT_RANK.get(policy.required_certification, 0)
        if have < need:
            violations.append(
                GateViolation(
                    rule="required_certification",
                    detail=f"Certification {result.certification} < required {policy.required_certification}",
                )
            )

    for threshold in policy.metric_thresholds:
        mr = result.metric_by_name(threshold.metric)
        if mr is None or not mr.is_applicable:
            continue
        if mr.score < threshold.min_score:
            violations.append(
                GateViolation(
                    rule=f"metric_threshold:{threshold.metric}",
                    detail=f"{threshold.metric} {mr.score:.2f} < required {threshold.min_score:.2f}",
                )
            )

    if policy.max_score_regression is not None and baseline is not None:
        drop = baseline.ninja_score - result.ninja_score
        if drop > policy.max_score_regression:
            violations.append(
                GateViolation(
                    rule="max_score_regression",
                    detail=(
                        f"Score regressed {drop:.1f} (baseline {baseline.ninja_score:.1f} "
                        f"→ {result.ninja_score:.1f}), exceeds max {policy.max_score_regression:.1f}"
                    ),
                )
            )

    if policy.fail_on_redteam_findings and redteam_findings:
        critical = [f for f in redteam_findings if f.get("severity") in ("critical", "high")]
        if critical:
            violations.append(
                GateViolation(
                    rule="fail_on_redteam_findings",
                    detail=f"{len(critical)} high/critical red-team finding(s) detected",
                )
            )

    return GateResult(
        policy_name=policy.name,
        passed=len(violations) == 0,
        violations=violations,
    )
