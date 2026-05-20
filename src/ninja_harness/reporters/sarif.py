"""
SARIF 2.1.0 reporter.

Emits Static Analysis Results Interchange Format output so Ninja Harness
findings can be consumed by GitHub Advanced Security, Azure DevOps, and other
SARIF-aware tooling.

Spec: https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html
"""

from __future__ import annotations

import json
from typing import Any

from ninja_harness import __version__
from ninja_harness.schemas import EvaluationResult

_SARIF_VERSION = "2.1.0"
_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"

# Map internal severity to SARIF result level
_SEVERITY_LEVEL = {
    "critical": "error",
    "high": "error",
    "medium": "warning",
    "low": "note",
}


def _metric_results_to_sarif(result: EvaluationResult) -> tuple[list[dict], list[dict]]:
    rules: list[dict] = []
    results: list[dict] = []
    seen_rules: set[str] = set()

    for mr in result.metric_results:
        if not mr.is_applicable or mr.passed:
            continue
        rule_id = f"metric/{mr.name}"
        if rule_id not in seen_rules:
            rules.append(
                {
                    "id": rule_id,
                    "name": mr.name,
                    "shortDescription": {"text": f"Ninja Harness metric: {mr.name}"},
                }
            )
            seen_rules.add(rule_id)
        message = mr.failure_reasons[0] if mr.failure_reasons else f"{mr.name} below threshold"
        results.append(
            {
                "ruleId": rule_id,
                "level": "warning",
                "message": {"text": f"{message} (score={mr.score:.2f})"},
                "properties": {"score": mr.score, "metric": mr.name},
            }
        )
    return rules, results


def _findings_to_sarif(findings: list[dict]) -> tuple[list[dict], list[dict]]:
    rules: list[dict] = []
    results: list[dict] = []
    seen_rules: set[str] = set()

    for f in findings:
        check = f.get("check", f.get("pattern", "redteam"))
        rule_id = f"security/{check}"
        if rule_id not in seen_rules:
            standards = f.get("standards", {})
            owasp_tags = [o["id"] for o in standards.get("owasp", [])]
            atlas_tags = [a["id"] for a in standards.get("atlas", [])]
            rules.append(
                {
                    "id": rule_id,
                    "name": check,
                    "shortDescription": {"text": f.get("description", check)},
                    "properties": {
                        "tags": ["security"] + owasp_tags + atlas_tags,
                        "owasp": owasp_tags,
                        "mitre_atlas": atlas_tags,
                    },
                }
            )
            seen_rules.add(rule_id)
        results.append(
            {
                "ruleId": rule_id,
                "level": _SEVERITY_LEVEL.get(f.get("severity", "medium"), "warning"),
                "message": {"text": f.get("description", check)},
                "properties": {
                    "location": f.get("location", ""),
                    "standards": f.get("standards", {}),
                },
            }
        )
    return rules, results


def to_sarif(
    result: EvaluationResult | None = None,
    findings: list[dict] | None = None,
) -> str:
    """
    Build a SARIF 2.1.0 document from an EvaluationResult and/or red-team
    findings. Returns a JSON string.
    """
    rules: list[dict] = []
    sarif_results: list[dict] = []

    if result is not None:
        r_rules, r_results = _metric_results_to_sarif(result)
        rules += r_rules
        sarif_results += r_results

    if findings:
        f_rules, f_results = _findings_to_sarif(findings)
        rules += f_rules
        sarif_results += f_results

    doc: dict[str, Any] = {
        "version": _SARIF_VERSION,
        "$schema": _SCHEMA,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "Ninja Harness",
                        "version": __version__,
                        "informationUri": "https://github.com/gagans23/ninja-harness",
                        "rules": rules,
                    }
                },
                "results": sarif_results,
            }
        ],
    }
    return json.dumps(doc, indent=2)
