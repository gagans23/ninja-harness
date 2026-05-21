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

## v0.3 — Reliability, Standards & CI Integration ✅

**Status**: Shipped. Research-driven hardening for production credibility.

- [x] **Statistical rigor** — multi-run aggregation: `pass@k`, `pass^k`, mean ± 95% CI, std, consistency, RELIABLE/FLAKY/UNRELIABLE verdict (`aggregate` command)
- [x] **OpenTelemetry GenAI adapter** — ingest `gen_ai.*` spans (`invoke_agent`, `execute_tool`) for true framework-agnosticism
- [x] **Safety standards mapping** — findings tagged with OWASP LLM Top 10 (2025) IDs + indicative MITRE ATLAS techniques
- [x] **SARIF 2.1.0 output** for GitHub Advanced Security / Azure DevOps
- [x] **JUnit XML output** for CI test panels
- [x] **GitHub Actions step summary** with status badge
- [x] **Policy gate** — `ninja-harness gate` with per-metric thresholds, score floors, regression guard, red-team blocking (CI exit codes)
- [x] **Judge bias mitigation** — `RubricJudge`, `PositionSwapJudge`, `EnsembleJudge`
- [x] `docs/evaluation_methodology.md` documenting the research basis

---

## v0.4 / v0.5 — End-to-End Harness ✅

Turned Ninja from a trace scorer into a full harness that *runs* agents.

- [x] **Closed loop** — `ninja-harness run` drives an agent, captures the trace, evaluates, and certifies (v0.4)
- [x] **Solver abstraction** — `CommandSolver` (any agent/any language), `ScriptedSolver`, `CallableSolver` (v0.4)
- [x] **Sandbox** — `LocalSandbox` (subprocess+timeout) and `DockerSandbox` (host isolation; no silent fallback) (v0.4)
- [x] **Reproducibility manifest** — versions, platform, git SHA, seed, trace SHA-256 (v0.4)
- [x] **Real benchmark loaders** — SWE-bench / τ-bench / GAIA on-disk formats → EvaluationCases (bring-your-own-dataset; no fabricated scores) (v0.5)
- [x] **Multi-turn user simulator** — `ScriptedUserSimulator` + `CallableUserSimulator` + `run_dialogue()` (pluggable model, deterministic default) (v0.5)
- [x] **Trace viewer UI** — self-contained static HTML trajectory explorer (`ninja-harness view`) (v0.5)
- [x] **Human annotation / calibration loop** — judge-vs-human MAE, Pearson/Spearman, Cohen's κ (`ninja-harness calibrate`) (v0.5)

---

## v0.6 — Adoption & Distribution ✅

Lower the barrier to download, try, and use.

- [x] **`ninja-harness serve`** — zero-dependency local web playground (stdlib only): paste a trace, evaluate in the browser, see certification + trajectory live
- [x] **PyPI packaging** — `pip install ninja-harness` / `pipx run` / `uvx`; `twine check` passes
- [x] **Release workflow** — tag-triggered build + PyPI trusted publishing (OIDC) + GitHub Release

---

## v0.7 — Agent CI & Deeper Quality ✅

From smoke-test to deep agent-quality testing.

- [x] **Output-hygiene metric** — penalizes noisy final answers; reported separately (weight 0)
- [x] **Scenario + failure eval pack** (`examples/scenarios/`) — real scenarios + failure modes (refuse token, refuse unauthorized messaging, sandbox offline, noisy vs concise browser), with a deliberately-failing exemplar that proves the harness catches leaks
- [x] **`/eval` suite summary** — compact, phone-friendly PASS/WARN/FAIL output (`suite --format summary`)
- [x] **Scheduled eval CI** (`eval-cron.yml`) — runs the suite on a cron, writes a summary, optional secret-guarded webhook notify (WhatsApp/Slack/Telegram)
- [x] **`run --repeat N`** — reliability aggregation (pass@k, pass^k) + `--save-baseline` (best run)
- [x] Hardened the OpenAI-key safety detector to catch hyphenated prefixes (`sk-proj-`, `sk-test-`)

---

## v1.0 — Polish & Stabilize

- [ ] `ninja-harness diff` — rich comparison of two results
- [ ] Judge plug-in extended to the Grounding metric
- [ ] `pytest` plugin: `pytest --ninja-harness-trace trace.json`
- [ ] Native OTLP/protobuf span ingest (beyond the simplified JSON span list)
- [ ] HTML reliability dashboard with trend charts across runs
- [ ] Stable public API (no breaking changes in 1.x), governance report templates, community plugins

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
