# Evaluation Methodology

This document explains the methodology behind Ninja Harness and the research it
draws on. The goal is credibility: every design choice should be defensible,
and we avoid claims we cannot support.

## 1. Trajectory-first, not answer-only

Most eval harnesses score the final answer. Ninja Harness scores the full
execution trajectory — plan, tool calls, observations, handoffs, guardrails,
recovery — because in production the *path* determines safety and reliability,
not just the destination. An agent can reach the right answer through unsafe
tool use, lost handoff context, or 40 wasteful loops.

## 2. Reliability over single-run scores (v0.3)

Agents are stochastic. A single run's NARI score is a point estimate with
unknown variance. Following the reliability framing popularized by tool-agent
benchmarks, Ninja Harness reports statistics across N repeated runs:

- **mean ± 95% confidence interval** (t-distribution approximation)
- **pass@k** — probability at least one of k trials certifies PASS
- **pass^k** — probability *all* k trials certify PASS (the reliability metric)
- **consistency** — `1 − normalized std`

The `pass^k < pass@k` gap is the classic "flaky agent" signature: it sometimes
works. A demo passes; production needs `pass^k → 1`.

```bash
ninja-harness aggregate run1.json run2.json run3.json --label my_task
```

> Note: these statistics describe the runs you actually executed. They are
> honest empirical summaries, not extrapolations or benchmark claims.

## 3. Deterministic-first scoring, judge-pluggable

v0.1–0.2 scoring is deterministic and reproducible (no API keys, no network).
For semantic comparison, the `Judge` interface lets you plug in:

- `DeterministicJudge` (default) — token overlap
- `EmbeddingJudge` — cosine similarity (`pip install ninja-harness[semantic]`)
- `RubricJudge` — weighted multi-criterion scoring
- Your own LLM-as-judge

### LLM-as-judge bias mitigation

The literature is consistent that untreated LLM judges exhibit **position**,
**verbosity**, **self-preference**, and **authority** biases. Ninja Harness
ships composable mitigations:

- `PositionSwapJudge` — evaluates both orderings and averages (position bias)
- `EnsembleJudge` — aggregates judges from different families (self-preference)
- `RubricJudge` — separates quality dimensions (single-axis bias)

Judges also drift over 60–90 days, so calibrate against a human-labeled set
periodically. Ninja Harness deliberately ships **no built-in LLM client** — you
supply the model, keeping the core deterministic and auditable.

## 4. Safety mapped to recognized standards (v0.3)

Safety findings are mapped to:

- **OWASP Top 10 for LLM Applications (2025)** — e.g. `LLM01:2025` Prompt
  Injection, `LLM02:2025` Sensitive Information Disclosure, `LLM06:2025`
  Excessive Agency
- **MITRE ATLAS** — indicative adversarial technique IDs

This makes findings useful for governance and audit, and lets them flow into
security tooling via SARIF. See `src/ninja_harness/standards.py`. MITRE ATLAS
IDs are indicative references, not exhaustive attribution.

## 5. CI/CD as a first-class consumer (v0.3)

Evaluation only changes behavior if it gates merges. Ninja Harness emits:

- **SARIF 2.1.0** — GitHub Advanced Security, Azure DevOps
- **JUnit XML** — test panels in GitHub Actions, GitLab CI, Jenkins
- **GitHub step summary** — Markdown + status badge in the run UI

…and provides a policy gate:

```bash
ninja-harness gate --results results.json --policy policy.yaml --baseline base.json
```

The gate exits non-zero on violation, so it fails the build. Teams define their
own thresholds (per-metric minimums, score floors, max regression) — this is the
"eval-driven development" pattern.

## 6. What Ninja Harness deliberately does *not* claim

- It is **not** a benchmark leaderboard and publishes no rankings.
- A passing score is **not** a safety certification — human review is required
  in high-risk domains (see [ethics.md](ethics.md)).
- Deterministic metrics catch known patterns; novel failures need humans.

## References

- τ-bench: A Benchmark for Tool-Agent-User Interaction (arXiv:2406.12045)
- OWASP Top 10 for LLM Applications (2025); OWASP Top 10 for Agentic Applications (2025)
- MITRE ATLAS — https://atlas.mitre.org/
- OpenTelemetry GenAI semantic conventions — https://opentelemetry.io/docs/specs/semconv/gen-ai/
- NIST AI Risk Management Framework (AI RMF)
- Literature on LLM-as-judge bias (position, verbosity, self-preference) and calibration
