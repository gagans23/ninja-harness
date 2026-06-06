# Changelog

All notable changes to Ninja Harness are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/) (pre-1.0: minor versions
may introduce features; patch versions are fixes).

## [Unreleased]

- Repository community-health files (CONTRIBUTING, CODE_OF_CONDUCT, SECURITY,
  CHANGELOG, CITATION, issue/PR templates), README badges, and repo metadata.

## [0.9.0] — 2026-06-06

### Added
- **Trajectory export** (`export.py` + `export` CLI) — turn *graded* agent runs
  into a training-ready JSONL dataset. Honest curation: an example is only
  written if its run clears a quality bar (certification PASS and/or a minimum
  NARI score), and the score + certification travel with every example. Two
  formats: `messages` (OpenAI-style chat with tool calls, for tool-calling SFT)
  and `sft` (`{prompt, completion}`). Optional **compression** (`--max-steps`,
  `--drop-observations`) trims low-signal steps without changing the task or the
  final answer. `TrajectoryExample` / `TrajectoryExportSummary` schemas.
  Deterministic, no LLM calls. Works off a `--suite` or a single `--trace`.

## [0.7.0] — 2026-05-21

### Added
- **Output-hygiene metric** (`scoring/output_hygiene.py`) — penalizes noisy final
  answers (logs, stack traces, warnings, bulk URLs); reported separately (not in
  the weighted composite, so existing scores are unchanged).
- **Scenario + failure eval pack** (`examples/scenarios/`) — real user scenarios
  and failure modes, with a deliberately-failing exemplar that proves the harness
  catches leaked secrets.
- **`suite --format summary`** — compact, phone/webhook-friendly PASS/WARN/FAIL report.
- **Scheduled eval CI** (`.github/workflows/eval-cron.yml`) + **`scripts/notify.py`**
  relaying summaries to Slack / Telegram / a generic webhook.
- **`run --repeat N`** — reliability aggregation (`pass@k`, `pass^k`) + `--save-baseline`.
- Explanatory landing page with visuals on the GitHub Pages site.

### Changed
- Hardened the OpenAI-key safety detector to catch hyphenated prefixes
  (`sk-proj-`, `sk-test-`) so obvious leaks FAIL instead of merely WARN.

## [0.6.0] — 2026-05-21

### Added
- **`ninja-harness serve`** — zero-dependency local web playground (stdlib only).
- **In-browser Pyodide playground** hosted on GitHub Pages.
- **PyPI packaging** + tag-triggered **release workflow** (trusted publishing).

## [0.5.0] — 2026-05-21

### Added
- **Benchmark loaders** for SWE-bench / GAIA / tau-bench on-disk formats.
- **Multi-turn user simulator** (`ScriptedUserSimulator`, `CallableUserSimulator`, `run_dialogue`).
- **Static HTML trace viewer** (`ninja-harness view`).
- **Judge calibration** (`ninja-harness calibrate`) — MAE, Pearson, Spearman, Cohen's κ.

## [0.4.0] — 2026-05-21

### Added
- **End-to-end `run`** — drive an agent, capture its trace, evaluate, and certify.
- **Solver abstraction** (`CommandSolver`, `ScriptedSolver`, `CallableSolver`).
- **Sandbox** (`LocalSandbox`, `DockerSandbox`).
- **Reproducibility manifest** (versions, platform, git SHA, seed, trace SHA-256).

## [0.3.0] — 2026-05-21

### Added
- **Statistical rigor** — `pass@k`, `pass^k`, confidence intervals, consistency (`aggregate`).
- **OpenTelemetry GenAI adapter**.
- **Safety standards mapping** — OWASP LLM Top 10 (2025) + MITRE ATLAS.
- **CI reporters** — SARIF 2.1.0, JUnit XML, GitHub step summary.
- **Policy gate** (`ninja-harness gate`) with per-metric thresholds + regression guard.
- **Judge bias mitigation** — `RubricJudge`, `PositionSwapJudge`, `EnsembleJudge`.

## [0.2.0] — 2026-05-21

### Added
- Real framework adapters: OpenAI Agents SDK, LangGraph, Hermes, CrewAI, AutoGen.
- Async + suite runner; `Judge` plug-in interface (`DeterministicJudge`, `EmbeddingJudge`).
- `eval --save-baseline`.

## [0.1.0] — 2026-05-21

### Added
- Initial release: trace-first evaluation with eight metrics and the Ninja Agent
  Reliability Index (NARI), Custom JSON adapter, deterministic scoring, red-team
  detection, CLI (`eval`, `score`, `report`, `redteam`, `validate`), and docs.

[Unreleased]: https://github.com/gagans23/ninja-harness/compare/v0.7.0...HEAD
[0.7.0]: https://github.com/gagans23/ninja-harness/releases/tag/v0.7.0
[0.6.0]: https://github.com/gagans23/ninja-harness/releases/tag/v0.6.0
[0.5.0]: https://github.com/gagans23/ninja-harness/releases/tag/v0.5.0
[0.4.0]: https://github.com/gagans23/ninja-harness/releases/tag/v0.4.0
[0.3.0]: https://github.com/gagans23/ninja-harness/releases/tag/v0.3.0
[0.2.0]: https://github.com/gagans23/ninja-harness/releases/tag/v0.2.0
[0.1.0]: https://github.com/gagans23/ninja-harness/releases/tag/v0.1.0
