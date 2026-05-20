# Ethical Use Statement

## Purpose

Ninja Harness is built for **defensive evaluation and responsible deployment** of agentic AI systems.

Its purpose is to help developers, researchers, and governance teams understand whether an AI agent behaves reliably, safely, and within the bounds of its intended design — *before* that agent is deployed into production.

---

## What Ninja Harness Is For

- Evaluating whether agents follow expected tool-use patterns
- Detecting credential exposure, injection compliance, or policy bypass in agent traces
- Measuring multi-agent handoff quality and context preservation
- Benchmarking agent efficiency and recovery from failures
- Supporting AI governance and audit workflows with reproducible trace records
- Building internal red-team tooling for defensive security evaluation of AI systems

---

## What Ninja Harness Is NOT For

Do not use Ninja Harness to:

- **Optimize agents for deception** — training agents to score well on safety metrics while actually engaging in deceptive behavior
- **Evade detection** — using safety findings to reverse-engineer evasion techniques
- **Surveillance abuse** — building systems that track, profile, or expose individuals without consent
- **Credential theft** — using credential detection patterns to harvest or exfiltrate credentials
- **Malware or weaponization** — applying agent evaluation to optimize offensive or destructive tools
- **Financial fraud** — evaluating agents designed for unauthorized financial access or manipulation
- **Data exfiltration** — using the harness to refine exfiltration patterns that bypass detection
- **Unauthorized access** — evaluating agents designed to access systems, data, or infrastructure without authorization
- **Bypassing human oversight** — deploying systems that use high Ninja Scores as a substitute for required human review

---

## Red Team Module

The red-team detection checks in `src/ninja_harness/redteam/` are **detection-only**. They:

- Scan existing trace text for patterns associated with risky behavior
- Return findings as structured data for human review
- Do **not** generate, teach, demonstrate, or improve harmful techniques

Using the red-team module to understand what risky patterns look like — in order to write better guardrails, improve agent policy, or conduct authorized security research — is an intended use.

Using it to produce a "safe-looking" trace that avoids detection while still performing harmful actions is an abuse of this tool.

---

## Safety Scores Are Not Substitutes for Human Review

A passing Ninja Score or safety metric does **not** certify that an agent is safe to deploy.

Automated evaluation catches known patterns. Novel behaviors, subtle misalignments, domain-specific risks, and high-stakes failure modes require human judgment.

For agents operating in:
- **Healthcare** — require clinical review and regulatory compliance
- **Legal** — require legal oversight and jurisdictional assessment
- **Finance** — require regulatory and fiduciary review
- **Critical infrastructure** — require security assessment and operational sign-off
- **Autonomous decision-making over people** — require ethics review and accountability frameworks

...do not rely on an automated harness score alone.

---

## Auditability and Accountability

Ninja Harness is designed to encourage:

1. **Trace retention**: Keep agent execution traces for audit, debugging, and retrospective review.
2. **Reproducibility**: Store eval cases alongside agent versions so evaluations can be re-run.
3. **Human accountability**: Assign named owners to agent deployments and keep decision logs.
4. **Transparency**: Publish evaluation methodology when deploying agents that affect others.

---

## Reporting Misuse

If you become aware of Ninja Harness being used to cause harm, please open an issue at:

https://github.com/gagans23/ninja-harness/issues

---

## Summary

Ninja Harness is a tool for making AI agents more trustworthy. Use it to build better, safer, more accountable systems — not to optimize for appearing safe while causing harm.
