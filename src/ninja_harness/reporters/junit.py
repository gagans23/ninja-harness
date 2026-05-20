"""
JUnit XML reporter.

Emits JUnit-style XML so Ninja Harness evaluations show up as test results in
CI systems (GitHub Actions, GitLab CI, Jenkins, etc.). Each metric becomes a
test case; non-passing metrics become failures.
"""

from __future__ import annotations

from xml.etree.ElementTree import Element, SubElement, tostring

from ninja_harness.schemas import EvaluationResult


def evaluation_to_junit(result: EvaluationResult) -> str:
    """Render an EvaluationResult as a JUnit XML string."""
    applicable = [m for m in result.metric_results if m.is_applicable]
    failures = sum(1 for m in applicable if not m.passed)

    testsuites = Element("testsuites")
    testsuite = SubElement(
        testsuites,
        "testsuite",
        {
            "name": f"ninja-harness:{result.run_id}",
            "tests": str(len(applicable) + 1),  # +1 for the certification gate
            "failures": str(failures + (1 if result.certification == "FAIL" else 0)),
        },
    )

    for m in applicable:
        testcase = SubElement(
            testsuite,
            "testcase",
            {"classname": "ninja_harness.metric", "name": m.name, "time": "0"},
        )
        if not m.passed:
            failure = SubElement(
                testcase,
                "failure",
                {"message": f"{m.name} score {m.score:.3f} did not pass"},
            )
            failure.text = "\n".join(m.failure_reasons) or "Metric did not pass."

    # Certification as its own test case
    cert_case = SubElement(
        testsuite,
        "testcase",
        {"classname": "ninja_harness.certification", "name": "certification", "time": "0"},
    )
    if result.certification == "FAIL":
        cert_failure = SubElement(
            cert_case,
            "failure",
            {"message": f"Certification FAIL (score={result.ninja_score:.1f})"},
        )
        cert_failure.text = "\n".join(result.top_failure_reasons) or "Certification failed."

    xml_bytes = tostring(testsuites, encoding="utf-8", xml_declaration=True)
    return xml_bytes.decode("utf-8")
