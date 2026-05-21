# CLAUDE.md — Ninja Harness

Context for Claude Code sessions working on this repository.

## Project

Ninja Harness is a trace-first evaluation harness for agentic AI systems.
It scores agent runs along multiple axes (goal success, tool call F1, handoff
integrity, grounding, safety, efficiency, recovery, stability) and issues a
composite Ninja Agent Reliability Index (NARI) score out of 100.

## Stack

- Python 3.11+
- Pydantic v2 (use `model_validator`, `field_validator`, not v1 patterns)
- Typer for the CLI (`cli.py`)
- Rich for terminal output
- PyYAML for eval case loading
- Pytest for tests

## Coding rules

1. All scoring is **deterministic in v0.1**. Do not add LLM API calls.
2. Do not add fake external integrations or invent benchmark claims.
3. Keep ethics and safety central — red-team checks are detection-only, never
   generative.
4. Type hints everywhere. No `Any` unless genuinely unavoidable.
5. No hardcoded API keys or secrets anywhere in the codebase.
6. Placeholder adapters (OpenAI, LangGraph, Hermes, CrewAI, AutoGen) must raise
   `NotImplementedError` with a clear message. Do not make them silently return
   empty results.
7. Run `pytest` before finalizing any change.
8. Keep the `schemas.py` models as the single source of truth for data shapes.
   Don't duplicate field definitions elsewhere.

## Directory layout

```
src/ninja_harness/
  __init__.py       — version + public re-exports
  cli.py            — Typer app
  schemas.py        — all Pydantic models
  runner.py         — orchestrates evaluation pipeline
  report.py         — Markdown + JSON report generation
  certification.py  — PASS/WARN/FAIL + grade logic
  scoring/          — one module per metric + ninja_score.py
  adapters/         — one module per framework trace format
  datasets/         — eval case loading helpers
  redteam/          — defensive safety detection checks
  examples/         — sample traces and eval cases
```

## Running locally

```bash
pip install -e ".[dev]"
pytest
ninja-harness validate --trace src/ninja_harness/examples/simple_agent_trace.json
ninja-harness eval \
  --trace src/ninja_harness/examples/simple_agent_trace.json \
  --case  src/ninja_harness/examples/evaluation_case.yaml
```

## v0.2 (shipped)

- Real adapters for OpenAI Agents SDK, LangGraph, Hermes, CrewAI, AutoGen (auto-detected)
- `SuiteRunner` with sync + async (`asyncio`) multi-case evaluation
- `Judge` plug-in for Goal Success (`DeterministicJudge` default, optional `EmbeddingJudge`)
- `ninja-harness suite --suite ... [--async]` and `eval --save-baseline`

When adding a new adapter: implement `can_parse()` (cheap, key-presence checks) and
`parse()` (pure, deterministic, raises `ValueError` on missing required fields), then
register it in `adapters/__init__.py`. Add an example trace under `examples/` and tests.

## v0.3 (shipped)

- Statistical rigor: `statistics.py` — `pass@k`, `pass^k`, mean ± 95% CI, consistency;
  `aggregate` command + `AggregateResult`/`ReliabilityStats` schemas
- OpenTelemetry GenAI adapter (`adapters/opentelemetry.py`) — `gen_ai.*` spans
- Safety standards mapping (`standards.py`) — OWASP LLM Top 10 2025 + MITRE ATLAS;
  only use accurate, verifiable IDs
- CI reporters (`reporters/`): SARIF 2.1.0, JUnit XML, GitHub step summary
- Policy gate (`policy.py`) + `gate` command for CI merge gating
- Judge combinators: `RubricJudge`, `PositionSwapJudge`, `EnsembleJudge`

Still no built-in LLM client — judges are user-supplied. Standards IDs must be
real (don't invent OWASP/ATLAS identifiers). Statistics describe observed runs,
not extrapolations — keep them honest.

## v0.4 (in progress — end-to-end harness)

- Closed loop shipped: `solver.py` (CommandSolver/ScriptedSolver/CallableSolver),
  `sandbox.py` (LocalSandbox/DockerSandbox), `provenance.py` (RunManifest),
  `TaskExecutor` in `runner.py`, `run` CLI command. TaskSpec/RunReport in schemas.
- CommandSolver contract: agent reads TaskSpec JSON on stdin, prints a trace JSON
  on stdout. Example: `examples/agents/echo_agent.py`.
- DockerSandbox must never silently fall back to local (defeats isolation).
- Still no bundled LLM agent — bring your own via a solver.

## v0.5 (shipped — completes the end-to-end harness)

- Benchmark loaders (`datasets/benchmarks.py`): SWE-bench/GAIA/tau-bench on-disk
  formats → EvaluationCase. Bring-your-own-dataset; NEVER fabricate scores.
- Multi-turn user simulator (`simulator.py`): ScriptedUserSimulator,
  CallableUserSimulator, `run_dialogue()` → AgentRun. No bundled model.
- HTML trace viewer (`reporters/html.py`): self-contained, offline, all content
  HTML-escaped. CLI `view`.
- Calibration (`calibration.py` + HumanLabel/CalibrationReport): MAE, Pearson,
  Spearman, Cohen's κ. CLI `calibrate`. Pure-Python stats (no numpy).

## Remaining (v0.6/v1.0)

- `diff`, grounding judge, pytest plugin, native OTLP/protobuf ingest, HTML
  reliability dashboard, stable API.
