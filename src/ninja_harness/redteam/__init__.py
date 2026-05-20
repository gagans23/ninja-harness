"""
Red-team detection module — DEFENSIVE USE ONLY.

These checks detect unsafe behavior patterns in agent traces.
They do not generate, teach, or demonstrate harmful content.
"""

from ninja_harness.redteam.data_exfiltration import DataExfiltrationDetector
from ninja_harness.redteam.prompt_injection import PromptInjectionDetector
from ninja_harness.redteam.tool_misuse import ToolMisuseDetector
from ninja_harness.redteam.unsafe_delegation import UnsafeDelegationDetector
from ninja_harness.standards import annotate_findings

__all__ = [
    "DataExfiltrationDetector",
    "PromptInjectionDetector",
    "ToolMisuseDetector",
    "UnsafeDelegationDetector",
]


def run_all_checks(run_dict: dict, with_standards: bool = True) -> list[dict]:
    """
    Run all red-team detection checks against a raw trace dict.

    When *with_standards* is True (default), each finding is annotated with the
    OWASP LLM Top 10 (2025) and indicative MITRE ATLAS references it maps to.
    """
    results = []
    detectors = [
        PromptInjectionDetector(),
        DataExfiltrationDetector(),
        ToolMisuseDetector(),
        UnsafeDelegationDetector(),
    ]
    for detector in detectors:
        findings = detector.detect(run_dict)
        results.extend(findings)
    if with_standards:
        annotate_findings(results)
    return results
