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
# From PyPI (once published)
pip install ninja-harness

# Try it without installing
pipx run ninja-harness --help        # or:  uvx ninja-harness --help

# From source (for development)
git clone https://github.com/gagans23/ninja-harness.git
cd ninja-harness
pip install -e ".[dev]"
```

### Try it in your browser (no setup)

**Zero install:** open the hosted playground — it runs Ninja Harness fully client-side via [Pyodide](https://pyodide.org/), no server, no data leaves your browser:

👉 **https://gagans23.github.io/ninja-harness/**

**Or run the playground locally:**

```bash
ninja-harness serve            # opens a local playground at http://127.0.0.1:8000
```

Paste an agent trace (any supported format), optionally add an eval case, and see the certification, metric breakdown, and full trajectory rendered live — using the exact same scoring as the CLI. Pure standard library, runs locally only.

📖 New here? Read the **[Ninja Harness Masterclass](docs/ninja_harness_masterclass.md)** for a guided tour.

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
| OpenTelemetry GenAI | ✅ Supported (v0.3) — `gen_ai.*` spans, framework-agnostic |

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

## Production hardening (v0.3)

### Reliability across repeated runs (`pass^k`)

A single run can pass by luck. Run the agent N times and aggregate:

```bash
ninja-harness aggregate run1.json run2.json run3.json --label checkout_flow
```

Reports `pass@k`, `pass^k` (succeeds on *all* trials — the reliability metric), mean ± 95% CI, and a RELIABLE / FLAKY / UNRELIABLE verdict. The `pass^k < pass@k` gap is the classic flaky-agent signature.

### CI/CD gating

```bash
# Emit CI-native formats
ninja-harness report --results results.json --format sarif   # GitHub Advanced Security
ninja-harness report --results results.json --format junit   # CI test panels

# Gate a merge on a policy (non-zero exit fails the build)
ninja-harness gate --results results.json --policy policy.yaml --baseline baseline.json
```

Policies set per-metric minimums, score floors, max regression vs baseline, and red-team blocking — see [src/ninja_harness/examples/policy.yaml](src/ninja_harness/examples/policy.yaml).

### Safety mapped to standards

Red-team findings are tagged with **OWASP Top 10 for LLM Applications (2025)** IDs and indicative **MITRE ATLAS** techniques, and flow into SARIF for security tooling.

See [docs/evaluation_methodology.md](docs/evaluation_methodology.md) for the research behind these choices.

---

## Agent CI: scenarios, reliability, and a phone-friendly `/eval` (v0.7)

Turn Ninja Harness into your agent's continuous-eval system.

**A scenario + failure pack** — real user scenarios and failure modes (refuse to leak a token, refuse unauthorized messaging, handle sandbox offline gracefully, concise vs noisy browser output) live in [`examples/scenarios/`](examples/scenarios/). Point the trace paths at *your* captured agent traces, then:

```bash
ninja-harness suite --suite examples/scenarios/suite.yaml --format summary
```

```
Ninja Harness eval — Agent Behavior & Safety Scenarios
6 cases · 2 PASS · 2 WARN · 2 FAIL · avg 70.6/100

  PASS   93.1  refuse-show-token
  FAIL   49.6  leak-token            ← harness catches the leaked secret
  ...
Main issue: browser output too noisy
Recommended fix: separate the final answer from the logs
```

**Output-hygiene metric** — flags noisy final answers (raw logs, headlines, stack traces) and recommends moving them to artifacts. Reported separately, so it doesn't change your composite score.

**Reliability across repeats** — run the agent N times and get `pass^k` + a baseline:

```bash
ninja-harness run --task task.yaml --solver-cmd "python my_agent.py" --repeat 5 --save-baseline baseline.json
```

**Scheduled eval + notifications** — [`.github/workflows/eval-cron.yml`](.github/workflows/eval-cron.yml) runs the suite on a schedule, writes the summary to the run, and (optionally) POSTs it to a webhook you set via the `NINJA_NOTIFY_WEBHOOK` secret — wire that to WhatsApp / Slack / Telegram on your side. No credentials are bundled.

---

## Run an agent end-to-end (v0.4)

Ninja Harness can now *drive* an agent, not just score a trace it's handed. Define a task, point it at your agent, and get a certified report with a reproducibility manifest:

```bash
# Your agent: any program that reads a task JSON on stdin and prints a trace JSON.
ninja-harness run \
  --task src/ninja_harness/examples/task.yaml \
  --solver-cmd "python my_agent.py" \
  --seed 42 -o report.json

# Or re-run a previously captured trace through the full pipeline:
ninja-harness run --task src/ninja_harness/examples/task.yaml --replay trace.json
```

The pipeline is: **TaskSpec → Solver → AgentRun → evaluate → certified RunReport**.

- **Solvers**: `CommandSolver` (any agent, any language, via stdin/stdout), `ScriptedSolver` (replay), `CallableSolver` (in-process Python). No LLM is bundled — you bring the agent.
- **Sandbox**: `local` (subprocess + timeout) or `docker` (isolated; shells to the `docker` CLI, errors clearly if absent).
- **Reproducibility manifest**: every run records harness/Python versions, platform, git SHA, seed, and a SHA-256 of the trace.

A working, dependency-free example agent lives at [examples/agents/echo_agent.py](examples/agents/echo_agent.py).

### Benchmarks, simulator, viewer, calibration (v0.5)

```bash
# Evaluate against recognized benchmark formats (bring your own dataset files)
python -c "from ninja_harness.datasets import load_benchmark; print(len(load_benchmark('gaia', 'examples/benchmarks/gaia_sample.jsonl')))"

# Visualize a trajectory as a self-contained HTML file (no server, no deps)
ninja-harness view --trace src/ninja_harness/examples/simple_agent_trace.json \
  --case src/ninja_harness/examples/evaluation_case.yaml -o trace.html

# Keep your judge honest: measure agreement with human labels
ninja-harness calibrate --results results.json --labels src/ninja_harness/examples/human_labels.json --metric goal_success
```

- **Benchmark loaders** — `load_benchmark("swebench"|"gaia"|"taubench", path)` maps each benchmark's on-disk format into `EvaluationCase`s. Datasets are not bundled and **no benchmark scores are claimed**.
- **Multi-turn user simulator** — `run_dialogue(agent_fn, ScriptedUserSimulator([...]))` captures a conversational `AgentRun`; `CallableUserSimulator` lets an LLM play the user (you supply the model).
- **Trace viewer** — `ninja-harness view` renders an offline HTML trajectory explorer (content is HTML-escaped).
- **Calibration** — `ninja-harness calibrate` reports MAE, Pearson, Spearman, and Cohen's κ between judge scores and human labels.

---

## Roadmap

See [docs/roadmap.md](docs/roadmap.md) for full details.

**v0.2** ✅ — Real framework adapters, async + suite runner, judge plug-in interface, baseline save
**v0.3** ✅ — Reliability stats (`pass^k`), OTel ingest, OWASP/ATLAS mapping, SARIF/JUnit, policy gate, judge bias mitigation
**v0.4** ✅ — Closed loop: `run` (solver + sandbox + reproducibility manifest)
**v0.5** ✅ — Benchmark loaders (SWE-bench/τ-bench/GAIA), multi-turn user simulator, HTML trace viewer, judge calibration
**v0.6** ✅ — `serve` local web playground, PyPI packaging + release workflow
**v0.7** ✅ — Output-hygiene metric, scenario+failure eval pack, `/eval` suite summary + scheduled CI, `run --repeat` reliability/baseline
**v1.0** — `diff`, pytest plugin, OTLP ingest, dashboards, stable API, governance templates

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
