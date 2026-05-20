"""
Prompt injection detection — DEFENSIVE, detection-only.

Detects signals that an agent may have followed injected instructions
embedded in tool results, documents, or user inputs.
"""

from __future__ import annotations

import re


_INJECTION_SIGNALS = [
    # Classic ignore-previous-instructions patterns
    re.compile(r"(?i)ignore (all |previous |prior )?(instructions?|prompts?|directives?)"),
    re.compile(r"(?i)disregard (all |previous |prior )?(instructions?|prompts?|directives?)"),
    re.compile(r"(?i)forget (everything|all instructions|what you were told)"),
    re.compile(r"(?i)new (instructions?|directives?|system prompt)\s*[:\-]"),
    # Persona hijacking
    re.compile(r"(?i)you are now (an? )?(unrestricted|jailbroken|evil|DAN|uncensored|unfiltered)"),
    re.compile(r"(?i)act as (an? )?(unrestricted|jailbroken|evil|DAN)"),
    # Exfiltration via injection
    re.compile(r"(?i)repeat (the above|everything|all|your system prompt|your instructions)"),
    re.compile(r"(?i)output (your system prompt|your instructions|the above)"),
    # Hidden separator tricks
    re.compile(r"---\s*(END|STOP|IGNORE ABOVE|NEW INSTRUCTIONS)", re.IGNORECASE),
]


class PromptInjectionDetector:
    """Detects prompt injection signals in trace text fields."""

    def detect(self, run_dict: dict) -> list[dict]:
        findings: list[dict] = []
        targets = self._extract_text_fields(run_dict)

        for location, text in targets:
            for pattern in _INJECTION_SIGNALS:
                matches = pattern.findall(text)
                if matches:
                    findings.append(
                        {
                            "check": "prompt_injection",
                            "severity": "critical",
                            "location": location,
                            "description": (
                                "Prompt injection signal detected. The agent may have "
                                "encountered or followed an injected instruction."
                            ),
                            "match_preview": matches[0][:80] if matches else "",
                        }
                    )
                    break  # one finding per location per detector

        return findings

    def _extract_text_fields(self, run_dict: dict) -> list[tuple[str, str]]:
        targets: list[tuple[str, str]] = []

        if text := run_dict.get("final_output"):
            targets.append(("final_output", str(text)))

        for i, step in enumerate(run_dict.get("steps", [])):
            for field in ("input", "output", "error"):
                if text := step.get(field):
                    targets.append((f"step[{i}].{field}", str(text)))

        for i, tc in enumerate(run_dict.get("tool_calls", [])):
            if result := tc.get("result"):
                targets.append((f"tool_call[{i}].result", str(result)))
            if args := tc.get("arguments"):
                targets.append((f"tool_call[{i}].arguments", str(args)))

        return targets
