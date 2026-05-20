# Ninja Harness

**Trace-first evals for agents that need to survive production.**

> Ninja Harness is a trace-aware evaluation harness for agentic AI systems. It helps developers test whether agents are reliable, safe, efficient, and production-ready — not just whether they produced a polished final answer.

---

## Why This Exists

Most agent evaluation today asks one question: *did the agent return the right answer?*

That misses almost everything that matters in production:

- Did the agent call the right tools in the right order?
- Did handoffs between agents preserve task context?
- Did guardrails fire when they should?
- Did the agent recover from tool failures?
- Did any step expose credentials or comply with injected instructions?
- Was the agent efficient, or did it loop and thrash?

Ninja Harness evaluates the **full execution trajectory** — not just the output:

```
Goal → Plan → Tool Call → Observation → Handoff → Guardrail → Recovery → Final Answer
```

---

## What Makes It Different

| Concern | Final-answer eval | Unit test | Ninja Harness |
|---|---|---|---|
| Execution path correctness | ✗ | Partial | ✓ |
| Tool call precision / recall | ✗ | Manual | ✓ |
| Multi-agent handoff integrity | ✗ | ✗ | ✓ |
| Safety / red-team detection | ✗ | ✗ | ✓ |
| Grounding against references | Partial | ✗ | ✓ |
| Efficiency analysis | ✗ | ✗ | ✓ |
| Recovery from failures | ✗ | ✗ | ✓ |
| Certification + grade | ✗ | ✗ | ✓ |
| Framework-agnostic | Varies | ✗ | ✓ |

---

## Installation

Requires Python 3.11+.

```bash
git clone https://github.com/gagans23/ninja-harness.git
cd ninja-harness
pip install -e ".[dev]"
```

Or install from PyPI (coming soon):

```bash
pip install ninja-harness
```

---

## Quickstart

### Evaluate a trace against an eval case

```bash
ninja-harness eval \
  --trace src/ninja_harness/examples/simple_agent_trace.json \
  --case src/ninja_harness/examples/evaluation_case.yaml
```

### Score a trace without a case (standalone)

```bash
ninja-harness score --trace src/ninja_harness/examples/simple_agent_trace.json
```

### Run red-team safety checks

```bash
ninja-harness redteam --trace src/ninja_harness/examples/simple_agent_trace.json
```

### Validate trace schema

```bash
ninja-harness validate --trace src/ninja_harness/examples/simple_agent_trace.json
```

### Generate a Markdown report

```bash
ninja-harness report --results results.json --format markdown
```

---

## Example Trace (Custom JSON)

```json
{
  "run_id": "run-001",
  "agent_name": "ResearchAgent",
  "task": "Summarize recent advances in transformer efficiency",
  "final_output": "Recent advances include FlashAttention-2, RoPE scaling, and MoE routing improvements.",
  "steps": [
    {
      "step_id": "s1",
      "agent_name": "ResearchAgent",
      "step_type": "plan",
      "output": "Search for papers, extract key advances, synthesize."
    },
    {
      "step_id": "s2",
      "agent_name": "ResearchAgent",
      "step_type": "action",
      "output": "Calling search tool"
    }
  ],
  "tool_calls": [
    {
      "tool_name": "web_search",
      "arguments": {"query": "transformer efficiency advances 2024"},
      "result": "FlashAttention-2 paper...",
      "status": "success"
    }
  ],
  "handoffs": [],
  "guardrail_events": []
}
```

### Example Output

```
╭─────────────────────────────────────────────────╮
│          Ninja Harness Evaluation Report         │
╰─────────────────────────────────────────────────╯

  Run ID   : run-001
  Agent    : ResearchAgent
  Task     : Summarize recent advances in transformer efficiency
  Score    : 82.4 / 100
  Grade    : B
  Status   : ✅ PASS

  Metric Breakdown
  ┌────────────────────────┬───────┬────────┐
  │ Metric                 │ Score │ Status │
  ├────────────────────────┼───────┼────────┤
  │ Goal Success           │  0.85 │ PASS   │
  │ Tool Call F1           │  0.90 │ PASS   │
  │ Handoff Integrity      │  N/A  │ SKIP   │
  │ Grounding              │  0.75 │ PASS   │
  │ Safety                 │  1.00 │ PASS   │
  │ Efficiency             │  0.80 │ PASS   │
  │ Recovery               │  0.60 │ WARN   │
  │ Stability              │  N/A  │ SKIP   │
  └────────────────────────┴───────┴────────┘
```

---

## Supported Metrics

| Metric | Weight | Description |
|---|---|---|
| Goal Success Score | 25% | Token-overlap of final output vs expected (LLM judge ready) |
| Tool Call F1 | 15% | Precision / recall of tool calls vs expected |
| Handoff Integrity | 15% | Completeness of agent handoff metadata |
| Grounding Score | 15% | Final output coverage against reference documents |
| Safety Score | 10% | Detection of credentials, injection, policy bypass |
| Efficiency Score | 10% | Steps, loops, latency, token cost |
| Recovery Score | 5% | Agent recovery from failures and errors |
| Stability Score | 5% | Regression vs prior baseline |

---

## Supported Frameworks

| Framework | Status |
|---|---|
| Custom JSON | ✅ Full support |
| OpenAI Agents SDK | ✅ Supported (v0.2) |
| LangGraph | ✅ Supported (v0.2) |
| Hermes multi-agent | ✅ Supported (v0.2) |
| CrewAI | ✅ Supported (v0.2) |
| AutoGen | ✅ Supported (v0.2) |

Framework adapters transform native traces into Ninja Harness's `AgentRun` schema. The correct adapter is auto-detected from the trace shape (or an explicit `"_source"` marker). Each adapter ships with an example trace under `src/ninja_harness/examples/`. See [docs/architecture.md](docs/architecture.md).

### Run a multi-framework suite

```bash
ninja-harness suite --suite src/ninja_harness/examples/example_suite.yaml --async
```

A suite evaluates many trace/case pairs in one run and reports pass rate and average score. Use `--async` to evaluate cases concurrently.

### Pluggable Goal Success judge

Goal Success uses a deterministic token-overlap judge by default (no API calls). Swap in semantic similarity or your own LLM-as-judge:

```python
from ninja_harness.runner import EvaluationRunner
from ninja_harness.scoring.judge import EmbeddingJudge  # pip install ninja-harness[semantic]

runner = EvaluationRunner(judge=EmbeddingJudge())
```

Ninja Harness ships no built-in LLM API client — you provide the model. This keeps the core library free of network calls and API keys.

---

## Roadmap

See [docs/roadmap.md](docs/roadmap.md) for full details.

**v0.2** ✅ — Real framework adapters, async + suite runner, judge plug-in interface, baseline save
**v0.3** — Built-in dataset registry, CI badge, SARIF output, `diff` command
**v0.4** — Multi-run aggregation, regression dashboards
**v1.0** — Stable API, governance report templates, community plugins

---

## Ethical Use

Ninja Harness is built for **defensive evaluation and responsible deployment**.

It is not a tool for optimizing agents to evade detection, deceive users, exfiltrate data, or bypass policy. Red-team checks are detection-only. Safety scores do not replace human review in high-risk domains.

Read the full statement: [docs/ethics.md](docs/ethics.md)

---

## Contributing

Contributions welcome. Please open an issue before large PRs.

- `make test` — run tests
- `make lint` — run ruff
- See [docs/architecture.md](docs/architecture.md) for design context

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

⭐ If Ninja Harness helps you catch an agent failure before production, consider giving the repo a star.
