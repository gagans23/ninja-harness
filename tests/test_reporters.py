"""Tests for CI/CD reporters (SARIF, JUnit, GitHub summary)."""

from __future__ import annotations

import json
from xml.etree.ElementTree import fromstring

from ninja_harness.reporters import (
    evaluation_to_junit,
    evaluation_to_step_summary,
    to_sarif,
)
from ninja_harness.schemas import EvaluationResult, MetricResult


def make_result(cert: str = "WARN") -> EvaluationResult:
    return EvaluationResult(
        run_id="run-x",
        metric_results=[
            MetricResult(name="goal_success", score=0.4, passed=False,
                         failure_reasons=["Output too divergent"]),
            MetricResult(name="safety", score=1.0, passed=True),
        ],
        ninja_score=72.0,
        grade="C",
        certification=cert,
        top_failure_reasons=["Output too divergent"],
    )


# --------------------------------------------------------------------------
# SARIF
# --------------------------------------------------------------------------

def test_sarif_is_valid_json_and_versioned() -> None:
    doc = json.loads(to_sarif(make_result()))
    assert doc["version"] == "2.1.0"
    assert doc["runs"][0]["tool"]["driver"]["name"] == "Ninja Harness"


def test_sarif_includes_failing_metric() -> None:
    doc = json.loads(to_sarif(make_result()))
    rule_ids = [r["ruleId"] for r in doc["runs"][0]["results"]]
    assert "metric/goal_success" in rule_ids


def test_sarif_includes_findings_with_standards() -> None:
    findings = [
        {"check": "prompt_injection", "severity": "critical",
         "description": "injection", "location": "final_output",
         "standards": {"owasp": [{"id": "LLM01:2025", "title": "Prompt Injection"}], "atlas": []}}
    ]
    doc = json.loads(to_sarif(None, findings=findings))
    results = doc["runs"][0]["results"]
    assert any(r["ruleId"] == "security/prompt_injection" for r in results)
    assert any(r["level"] == "error" for r in results)


# --------------------------------------------------------------------------
# JUnit
# --------------------------------------------------------------------------

def test_junit_is_well_formed_xml() -> None:
    xml = evaluation_to_junit(make_result())
    root = fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
    assert root.tag == "testsuites"
    suite = root.find("testsuite")
    assert suite is not None
    assert int(suite.get("tests")) >= 2


def test_junit_marks_failures() -> None:
    xml = evaluation_to_junit(make_result(cert="FAIL"))
    root = fromstring(xml.encode("utf-8"))
    failures = root.iter("failure")
    assert len(list(failures)) >= 1


def test_junit_passing_result_no_metric_failures() -> None:
    result = EvaluationResult(
        run_id="r", ninja_score=95, grade="A", certification="PASS",
        metric_results=[MetricResult(name="safety", score=1.0, passed=True)],
    )
    xml = evaluation_to_junit(result)
    root = fromstring(xml.encode("utf-8"))
    assert len(list(root.iter("failure"))) == 0


# --------------------------------------------------------------------------
# GitHub step summary
# --------------------------------------------------------------------------

def test_step_summary_contains_badge_and_report() -> None:
    summary = evaluation_to_step_summary(make_result())
    assert "img.shields.io" in summary
    assert "Ninja Harness Evaluation Report" in summary
