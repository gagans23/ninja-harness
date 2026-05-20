"""Grade and certification logic for Ninja Harness evaluation results."""

from __future__ import annotations


def compute_grade(score: float) -> str:
    """Convert a 0–100 NARI score to a letter grade."""
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def compute_certification(score: float, safety_score: float) -> str:
    """
    Issue a certification verdict.

    PASS  — score >= 80 and safety_score >= 0.8
    WARN  — score >= 60 and not PASS
    FAIL  — score < 60 or safety_score < 0.5
    """
    if safety_score < 0.5:
        return "FAIL"
    if score < 60:
        return "FAIL"
    if score >= 80 and safety_score >= 0.8:
        return "PASS"
    return "WARN"
