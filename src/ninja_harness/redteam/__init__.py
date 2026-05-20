"""
Red-team detection module — DEFENSIVE USE ONLY.

These checks detect unsafe behavior patterns in agent traces.
They do not generate, teach, or demonstrate harmful content.
"""

from ninja_harness.redteam.data_exfiltration import DataExfiltrationDetector
from ninja_harness.redteam.prompt_injection import PromptInjectionDetector
from ninja_harness.redteam.tool_misuse import ToolMisuseDetector
from ninja_harness.redteam.unsafe_delegation import UnsafeDelegationDetector

__all__ = [
    "DataExfiltrationDetector",
    "PromptInjectionDetector",
    "ToolMisuseDetector",
    "UnsafeDelegationDetector",
]


def run_all_checks(run_dict: dict) -> list[dict]:
    """Run all red-team detection checks against a raw trace dict."""
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
    return results
