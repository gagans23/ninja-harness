# Roadmap

## v0.1 (current)

**Goal**: Working end-to-end evaluation harness for Custom JSON traces.

- [x] Full Pydantic v2 schema (`AgentRun`, `EvaluationCase`, `EvaluationResult`, etc.)
- [x] `CustomJsonAdapter` — full implementation
- [x] Placeholder adapters: OpenAI Agents SDK, LangGraph, Hermes, CrewAI, AutoGen
- [x] Eight scoring metrics: Goal Success, Tool Call F1, Handoff Integrity, Grounding, Safety, Efficiency, Recovery, Stability
- [x] NARI composite score (0–100), grade (A–F), certification (PASS/WARN/FAIL)
- [x] Typer CLI with `eval`, `score`, `validate`, `redteam`, `report` commands
- [x] Rich terminal output, JSON output, Markdown report
- [x] Red-team detection module (prompt injection, data exfiltration, tool misuse, unsafe delegation)
- [x] Pytest suite covering all major modules
- [x] GitHub Actions CI
- [x] CLAUDE.md for Claude Code sessions

---

## v0.2 — Framework Adapters + Async Runner ✅

**Status**: Shipped. Full adapter support for major frameworks.

- [x] **OpenAI Agents SDK adapter** — parses `RunResult` items (`message_output_item`, `tool_call_item`, `handoff_output_item`) and usage
- [x] **LangGraph adapter** — parses node execution records, `ToolNode` calls, and conditional-edge transfers
- [x] **Hermes adapter** — parses multi-agent message arrays with function calls; infers handoffs from agent name changes
- [x] **CrewAI adapter** — parses Crew task logs, `tools_used`, and `delegated_from` delegation events
- [x] **AutoGen adapter** — parses chat history, function call blocks, and group-chat turn transfers
- [x] Adapter auto-detection from trace shape or `"_source"` marker
- [x] Async evaluation runner (`asyncio` worker pool) for concurrent multi-case execution
- [x] YAML eval suite runner: `ninja-harness suite --suite evals/my_suite.yaml [--async]`
- [x] `Judge` plug-in interface for Goal Success (`DeterministicJudge` default, `EmbeddingJudge` optional)
- [x] `--save-baseline` option on `eval` for stability comparison
- [x] Optional semantic similarity via `pip install ninja-harness[semantic]` (sentence-transformers, no API key)

---

## v0.3 — Dataset Registry + CI Integration

- [ ] Built-in eval case dataset registry (curated multi-domain eval cases)
- [ ] CI badge generator (`ninja-harness badge --results results.json`)
- [ ] SARIF output for GitHub Advanced Security integration
- [ ] `ninja-harness diff` — compare two EvaluationResult JSON files
- [ ] Judge plug-in extended to the Grounding metric
- [ ] Per-metric pass thresholds configurable in eval case YAML
- [ ] `pytest` plugin: `pytest --ninja-harness-trace trace.json`
- [ ] OpenTelemetry trace ingest (auto-convert OTEL spans to AgentRun)
- [ ] Token-budget / cost efficiency scoring improvements

---

## v0.4 — Dashboards + Multi-Run Analysis

- [ ] Multi-run aggregation: `ninja-harness aggregate --results results/*.json`
- [ ] Regression dashboard (HTML report with trend charts)
- [ ] Agent comparison: `ninja-harness compare --a run1.json --b run2.json`
- [ ] Eval case auto-generation from human-verified runs
- [ ] Structured annotation support (human labels on trace steps)
- [ ] Webhook integration for CI/CD pipelines

---

## v1.0 — Stable API + Governance Templates

- [ ] Stable public Python API (no breaking changes in 1.x)
- [ ] Governance report templates (AI governance, EU AI Act readiness checklist)
- [ ] Signed evaluation reports for audit trails
- [ ] Community plugin system for custom scorers and adapters
- [ ] Hosted leaderboard option (opt-in, anonymized)
- [ ] Full documentation site

---

## Non-Goals

These are explicitly out of scope:

- **Agent framework**: Ninja Harness evaluates agents; it does not build or run them.
- **LLM training/fine-tuning**: Not an RLHF or fine-tuning pipeline.
- **Hosted SaaS**: v1.0 targets an open-source library, not a managed service.
- **Benchmark claims**: Ninja Harness does not publish or maintain a leaderboard by default.
