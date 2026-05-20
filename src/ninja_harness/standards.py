"""
Security-standard mapping for safety findings.

Maps Ninja Harness detectors to recognized AI-security standards so that
safety findings are useful for governance, audit, and CI security tooling:

- OWASP Top 10 for LLM Applications (2025)
- MITRE ATLAS adversarial technique IDs (indicative)

References:
- https://owasp.org/www-project-top-10-for-large-language-model-applications/
- https://genai.owasp.org/  (Top 10 for Agentic Applications, Dec 2025)
- https://atlas.mitre.org/

Only IDs that map cleanly to a detector are included. MITRE ATLAS technique
IDs are provided as indicative references, not exhaustive attribution.
"""

from __future__ import annotations

# OWASP Top 10 for LLM Applications (2025)
OWASP_LLM_2025: dict[str, str] = {
    "LLM01:2025": "Prompt Injection",
    "LLM02:2025": "Sensitive Information Disclosure",
    "LLM05:2025": "Improper Output Handling",
    "LLM06:2025": "Excessive Agency",
    "LLM07:2025": "System Prompt Leakage",
    "LLM10:2025": "Unbounded Consumption",
}

# MITRE ATLAS techniques (indicative subset)
MITRE_ATLAS: dict[str, str] = {
    "AML.T0051": "LLM Prompt Injection",
    "AML.T0054": "LLM Jailbreak",
    "AML.T0057": "LLM Data Leakage",
}

# detector/pattern key -> standard references
_MAPPING: dict[str, dict[str, list[str]]] = {
    # red-team checks
    "prompt_injection": {"owasp": ["LLM01:2025"], "atlas": ["AML.T0051"]},
    "data_exfiltration": {"owasp": ["LLM02:2025"], "atlas": ["AML.T0057"]},
    "tool_misuse": {"owasp": ["LLM06:2025", "LLM05:2025"], "atlas": []},
    "unsafe_delegation": {"owasp": ["LLM06:2025"], "atlas": []},
    # safety scorer pattern names
    "api_key_openai": {"owasp": ["LLM02:2025"], "atlas": []},
    "api_key_anthropic": {"owasp": ["LLM02:2025"], "atlas": []},
    "api_key_google": {"owasp": ["LLM02:2025"], "atlas": []},
    "aws_access_key": {"owasp": ["LLM02:2025"], "atlas": []},
    "password_field": {"owasp": ["LLM02:2025"], "atlas": []},
    "bearer_token": {"owasp": ["LLM02:2025"], "atlas": []},
    "prompt_injection_compliance": {"owasp": ["LLM01:2025"], "atlas": ["AML.T0051"]},
    "policy_bypass_language": {"owasp": ["LLM01:2025"], "atlas": ["AML.T0054"]},
    "data_exfiltration_url": {"owasp": ["LLM02:2025"], "atlas": ["AML.T0057"]},
    "unauthorized_file_access": {"owasp": ["LLM06:2025"], "atlas": []},
    "unsafe_tool_escalation": {"owasp": ["LLM06:2025", "LLM05:2025"], "atlas": []},
    "hidden_instruction": {"owasp": ["LLM01:2025"], "atlas": ["AML.T0051"]},
}


def lookup(key: str) -> dict:
    """
    Resolve a detector/pattern key to standard references with titles.

    Returns a dict with 'owasp' and 'atlas' lists of {id, title}. Unknown keys
    return empty lists rather than raising.
    """
    refs = _MAPPING.get(key, {"owasp": [], "atlas": []})
    return {
        "owasp": [{"id": i, "title": OWASP_LLM_2025.get(i, "")} for i in refs.get("owasp", [])],
        "atlas": [{"id": i, "title": MITRE_ATLAS.get(i, "")} for i in refs.get("atlas", [])],
    }


def annotate_findings(findings: list[dict]) -> list[dict]:
    """
    Attach a 'standards' field to each finding based on its 'check' or
    'pattern' key. Mutates and returns the same list for convenience.
    """
    for f in findings:
        key = f.get("check") or f.get("pattern") or ""
        f["standards"] = lookup(key)
    return findings


def owasp_ids_for(key: str) -> list[str]:
    """Return just the OWASP LLM Top 10 (2025) IDs for a detector key."""
    return _MAPPING.get(key, {}).get("owasp", [])
