# Ninja Harness vs Other Approaches

## The Core Distinction

> **Ninja Harness is not an agent framework. It is an agent behavior certification harness.**

It does not build, run, or orchestrate agents. It evaluates traces left by agents — regardless of which framework produced them.

---

## Comparison Table

| Approach | What It Tests | What It Misses |
|---|---|---|
| Final-answer eval | Output correctness | Everything that happened to produce the output |
| Unit tests | Individual functions | Agent emergent behavior, multi-step dynamics |
| Benchmark-only | Aggregate task performance | Per-run trajectory quality, safety, handoffs |
| Observability tools | What happened (logging/tracing) | Whether what happened was *correct* |
| Governance checklists | Policy compliance (static) | Runtime behavior evidence |
| **Ninja Harness** | Full execution trajectory quality | Ground truth (needs human for novel failures) |

---

## Final-Answer-Only Evaluation

**What it does**: Compare the agent's final output to a reference answer. Often using BLEU, ROUGE, exact match, or LLM-as-judge.

**What it misses**:
- The agent might have reached the right answer via wrong tool calls
- The agent might have called privileged tools without authorization
- Multi-agent handoffs might have lost critical context
- The agent might have looped 40 times before producing the right answer
- The agent might have been exploited by a prompt injection in a tool result

**Ninja Harness adds**: trajectory scoring (tool F1, handoff integrity, safety, efficiency, recovery) on top of output evaluation.

---

## Unit Tests

**What they do**: Verify that individual functions behave correctly with controlled inputs.

**What they miss**:
- Emergent behaviors when components interact
- Agent decision-making under real tool uncertainty
- Multi-agent coordination failures
- Safety properties of dynamic agent behavior

**Ninja Harness adds**: black-box evaluation of full agent execution traces — no mocking required.

---

## Benchmark-Only Evaluation

**What it does**: Score an agent across a dataset of tasks to produce an aggregate pass rate or score.

**What it misses**:
- Per-run diagnosis: *why* did specific runs fail?
- Process quality: even failed runs might have correct intermediate steps
- Safety: a high benchmark score doesn't mean the agent is safe
- Production readiness: benchmarks are typically clean inputs; production is messy

**Ninja Harness adds**: per-run metric breakdown, certification, and specific failure reasons — not just a headline number.

---

## Observability Tools (e.g., LangSmith, Arize, Helicone)

**What they do**: Capture and display agent execution traces — logs, spans, latency, token counts.

**What they miss**:
- Evaluation logic: they show *what happened*, not *whether it was correct*
- Safety scoring: not their primary purpose
- Certification: they don't issue PASS/WARN/FAIL

**Ninja Harness adds**: scoring, safety detection, handoff integrity checking, and certification on top of the traces these tools collect. They are complementary, not competing.

---

## Governance Checklists

**What they do**: Provide static policy questions ("does the system have a human-in-the-loop?") for regulatory or procurement compliance.

**What they miss**:
- Runtime behavior evidence
- Trace-level safety verification
- Quantitative scoring

**Ninja Harness adds**: evidence-based, trace-grounded evaluation that can populate governance documentation with actual runtime data.

---

## Where Ninja Harness Fits

```
Development → Unit tests, integration tests
Evaluation  → Ninja Harness (trace-first evals)
Monitoring  → Observability tools (LangSmith, Arize, etc.)
Compliance  → Governance checklists + Ninja Harness reports as evidence
Production  → All of the above + human review for high-risk domains
```

Ninja Harness occupies the **evaluation** layer — between development testing and production monitoring. It answers the question: "Is this agent ready for the next environment?"
