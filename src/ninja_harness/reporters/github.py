"""
GitHub Actions step-summary reporter.

Produces a Markdown summary suitable for $GITHUB_STEP_SUMMARY, so evaluation
results render directly in the GitHub Actions run UI.
"""

from __future__ import annotations

import os

from ninja_harness.report import generate_markdown_report
from ninja_harness.schemas import EvaluationResult

_CERT_BADGE = {
    "PASS": "![PASS](https://img.shields.io/badge/Ninja%20Harness-PASS-brightgreen)",
    "WARN": "![WARN](https://img.shields.io/badge/Ninja%20Harness-WARN-yellow)",
    "FAIL": "![FAIL](https://img.shields.io/badge/Ninja%20Harness-FAIL-red)",
}


def evaluation_to_step_summary(result: EvaluationResult) -> str:
    """Build a Markdown step summary with a status badge + full report."""
    badge = _CERT_BADGE.get(result.certification, "")
    header = f"{badge}\n\n**Ninja Score: {result.ninja_score:.1f}/100 — Grade {result.grade}**\n\n"
    return header + generate_markdown_report(result)


def write_step_summary(content: str) -> bool:
    """
    Append *content* to the GitHub step summary file if $GITHUB_STEP_SUMMARY is
    set. Returns True if written, False if not running under GitHub Actions.
    """
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return False
    with open(path, "a") as f:
        f.write(content + "\n")
    return True
