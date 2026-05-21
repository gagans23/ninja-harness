# Launch Kit

Ready-to-paste copy for launching Ninja Harness. Publishing is your call — these
are drafts. Keep the claims honest (no "world's best", no fabricated benchmark
numbers).

## Positioning

> Ninja Harness is the **certification layer for the agent-harness era** — grade
> any agent (or runtime harness) before it ships. Trace-first, framework-agnostic,
> reliability-aware (`pass^k`), safety-mapped (OWASP/MITRE), CI-native.

It is an **evaluation harness**, not a runtime/agent harness (like Hermes Agent or
Claude Code). It complements them — someone has to grade the agents they run.

## One-liners

- "Trace-first evals for agents that need to survive production."
- "Grade the harnesses."
- "The trust layer for autonomous agents."

## X / Twitter thread

```
1/ Most agent evals only check the final answer.
But production failures live in the *path* — wrong tool calls, lost handoffs,
prompt injection, 40 wasteful loops.
Ninja Harness scores the full trajectory. Open source 🥷
github.com/gagans23/ninja-harness

2/ Framework-agnostic: bring an OpenAI Agents SDK / LangGraph / CrewAI / AutoGen
trace — or any OpenTelemetry GenAI trace — and get one certified report.

3/ It reports pass^k, not just pass@1. Run N times; if it only passes sometimes,
that's the flaky-agent signature. Demos pass. Production needs pass^k → 1.

4/ Safety findings map to OWASP LLM Top 10 (2025) + MITRE ATLAS and export to
SARIF/JUnit, so you can gate merges in CI.

5/ v0.5 closes the loop: `ninja-harness run` drives your agent, captures the
trace, evaluates, and certifies — with a reproducibility manifest.

⭐ If it helps you catch a failure before prod: github.com/gagans23/ninja-harness
```

## LinkedIn

```
I built Ninja Harness — an open-source, trace-first evaluation + certification
harness for AI agents.

Most agent testing asks "did it return the right answer?" That misses what breaks
in production: the wrong tools got called, a handoff dropped context, a prompt
injection slipped through, or the agent looped 40 times.

Ninja Harness scores the whole execution trajectory and issues a PASS/WARN/FAIL
certification. It's framework-agnostic (OpenTelemetry ingest), reports pass^k
reliability across repeated runs, maps safety findings to OWASP LLM Top 10 + MITRE
ATLAS, gates merges via SARIF/JUnit, and now runs agents end to end with a
reproducibility manifest.

Not another agent framework — the trust layer for the ones you already use.
Apache-2.0: github.com/gagans23/ninja-harness

#AIagents #LLM #AIsafety #MLOps #opensource
```

## Show HN

- Title: `Show HN: Ninja Harness – trace-first evals and certification for AI agents`
- Body:
```
Ninja Harness scores the full agent trajectory (plan → tool calls → handoffs →
guardrails → recovery → answer), not just the final output, and issues a
PASS/WARN/FAIL certification.

Framework-agnostic via OpenTelemetry GenAI ingest. Reports pass^k reliability
(single-run scores lie — agents are stochastic). Maps safety findings to OWASP LLM
Top 10 (2025) + MITRE ATLAS. Emits SARIF/JUnit for CI gating. v0.5 closes the loop:
`ninja-harness run` drives your agent, captures the trace, evaluates, certifies,
and records a reproducibility manifest. Deterministic-first; no bundled LLM (you
supply any judge or agent).

It is NOT a runtime/agent harness like Hermes or Claude Code — it's the layer that
grades them. Python 3.11+, Apache-2.0.

Honest about limits: benchmark datasets aren't bundled and no benchmark scores are
claimed; a passing score isn't a safety guarantee (human review still required).

Repo: https://github.com/gagans23/ninja-harness
```

## Reddit (r/LLMDevs, r/LocalLLaMA, r/MachineLearning [P])

```
Title: Open-sourced a trace-first evaluation + certification harness for AI agents

Scores the whole trajectory and certifies PASS/WARN/FAIL, ingests OpenTelemetry
GenAI traces (works with any framework), reports pass^k reliability, maps safety
findings to OWASP LLM Top 10 + MITRE ATLAS with SARIF/JUnit for CI, and can run
agents end to end. Not an agent framework — the layer that grades agents. Feedback
on the metric design welcome: github.com/gagans23/ninja-harness
```

## Launch-day checklist

1. Add a short GIF/asciinema of the Rich output + the HTML viewer to the README.
2. Post Show HN (Tue–Thu, ~8–10am ET). Reply to every comment in the first 3 hours.
3. Cross-post the X thread + LinkedIn.
4. Seed r/LLMDevs and r/LocalLLaMA.
5. Submit to relevant awesome-lists (e.g. awesome-harness-engineering, awesome-LLMOps).
6. Cut a GitHub Release: `gh release create v0.5.0 --generate-notes`.
