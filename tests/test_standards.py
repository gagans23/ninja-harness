"""Tests for the security-standards mapping."""

from __future__ import annotations

from ninja_harness.standards import (
    OWASP_LLM_2025,
    annotate_findings,
    lookup,
    owasp_ids_for,
)


def test_owasp_catalog_has_known_ids() -> None:
    assert "LLM01:2025" in OWASP_LLM_2025
    assert OWASP_LLM_2025["LLM01:2025"] == "Prompt Injection"
    assert "LLM06:2025" in OWASP_LLM_2025


def test_lookup_prompt_injection() -> None:
    refs = lookup("prompt_injection")
    owasp_ids = [o["id"] for o in refs["owasp"]]
    atlas_ids = [a["id"] for a in refs["atlas"]]
    assert "LLM01:2025" in owasp_ids
    assert "AML.T0051" in atlas_ids


def test_lookup_unknown_key_is_empty() -> None:
    refs = lookup("does_not_exist")
    assert refs["owasp"] == []
    assert refs["atlas"] == []


def test_owasp_ids_for_tool_misuse() -> None:
    ids = owasp_ids_for("tool_misuse")
    assert "LLM06:2025" in ids


def test_annotate_findings_by_check() -> None:
    findings = [{"check": "data_exfiltration", "severity": "critical"}]
    annotate_findings(findings)
    assert "standards" in findings[0]
    assert findings[0]["standards"]["owasp"][0]["id"] == "LLM02:2025"


def test_annotate_findings_by_pattern() -> None:
    findings = [{"pattern": "api_key_openai", "severity": "critical"}]
    annotate_findings(findings)
    assert findings[0]["standards"]["owasp"][0]["id"] == "LLM02:2025"


def test_annotate_resolves_titles() -> None:
    findings = [{"check": "prompt_injection"}]
    annotate_findings(findings)
    titles = [o["title"] for o in findings[0]["standards"]["owasp"]]
    assert "Prompt Injection" in titles
