"""CLI smoke tests using Typer's test runner."""

from __future__ import annotations

import sys
from pathlib import Path

from typer.testing import CliRunner

from ninja_harness.cli import app

TRACE = str(Path("src/ninja_harness/examples/simple_agent_trace.json"))
CASE = str(Path("src/ninja_harness/examples/evaluation_case.yaml"))
FAILING_TRACE = str(Path("src/ninja_harness/examples/failing_agent_trace.json"))
SUITE = str(Path("src/ninja_harness/examples/example_suite.yaml"))
OPENAI_TRACE = str(Path("src/ninja_harness/examples/openai_agents_trace.json"))
OTEL_TRACE = str(Path("src/ninja_harness/examples/opentelemetry_trace.json"))
TASK = str(Path("src/ninja_harness/examples/task.yaml"))
ECHO_AGENT = str(Path("examples/agents/echo_agent.py"))

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "ninja-harness" in result.output.lower()


def test_validate_valid_trace() -> None:
    result = runner.invoke(app, ["validate", "--trace", TRACE])
    assert result.exit_code == 0
    assert "Valid" in result.output or "ResearchAgent" in result.output


def test_validate_missing_file() -> None:
    result = runner.invoke(app, ["validate", "--trace", "nonexistent.json"])
    assert result.exit_code != 0


def test_score_command() -> None:
    result = runner.invoke(app, ["score", "--trace", TRACE, "--format", "json"])
    assert result.exit_code in (0, 2)  # 0=PASS/WARN, 2=FAIL
    assert "ninja_score" in result.output


def test_eval_command_json() -> None:
    result = runner.invoke(
        app, ["eval", "--trace", TRACE, "--case", CASE, "--format", "json"]
    )
    assert result.exit_code in (0, 2)
    assert "ninja_score" in result.output


def test_eval_command_rich() -> None:
    result = runner.invoke(
        app, ["eval", "--trace", TRACE, "--case", CASE, "--format", "rich"]
    )
    assert result.exit_code in (0, 2)
    assert "ResearchAgent" in result.output or "Score" in result.output


def test_eval_command_markdown() -> None:
    result = runner.invoke(
        app, ["eval", "--trace", TRACE, "--case", CASE, "--format", "markdown"]
    )
    assert result.exit_code in (0, 2)
    assert "# Ninja Harness" in result.output


def test_redteam_clean_trace() -> None:
    result = runner.invoke(app, ["redteam", "--trace", TRACE])
    # Clean trace should exit 0
    assert result.exit_code == 0


def test_redteam_json_output() -> None:
    result = runner.invoke(app, ["redteam", "--trace", TRACE, "--format", "json"])
    assert result.exit_code == 0
    assert "[]" in result.output or '"check"' in result.output


def test_score_outputs_grade() -> None:
    result = runner.invoke(app, ["score", "--trace", TRACE, "--format", "json"])
    assert "grade" in result.output
    assert "certification" in result.output


def test_validate_openai_agents_trace() -> None:
    result = runner.invoke(app, ["validate", "--trace", OPENAI_TRACE])
    assert result.exit_code == 0
    assert "OpenAIAgentsAdapter" in result.output


def test_suite_command_rich() -> None:
    result = runner.invoke(app, ["suite", "--suite", SUITE])
    # Suite has WARN cases but no FAIL/errors → exit 0
    assert result.exit_code == 0
    assert "Ninja Harness Suite" in result.output or "Avg score" in result.output


def test_suite_command_json() -> None:
    result = runner.invoke(app, ["suite", "--suite", SUITE, "--format", "json"])
    assert result.exit_code == 0
    assert "average_score" in result.output or "results" in result.output


def test_suite_command_async() -> None:
    result = runner.invoke(app, ["suite", "--suite", SUITE, "--async"])
    assert result.exit_code == 0


def test_eval_save_baseline(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    result = runner.invoke(
        app, ["eval", "--trace", TRACE, "--case", CASE, "--save-baseline", str(baseline), "--format", "json"]
    )
    assert result.exit_code in (0, 2)
    assert baseline.exists()


def test_validate_otel_trace() -> None:
    result = runner.invoke(app, ["validate", "--trace", OTEL_TRACE])
    assert result.exit_code == 0
    assert "OpenTelemetryAdapter" in result.output


def test_report_sarif_format(tmp_path: Path) -> None:
    res = tmp_path / "r.json"
    runner.invoke(app, ["score", "--trace", TRACE, "-o", str(res), "--format", "json"])
    result = runner.invoke(app, ["report", "--results", str(res), "--format", "sarif"])
    assert result.exit_code == 0
    assert "2.1.0" in result.output


def test_report_junit_format(tmp_path: Path) -> None:
    res = tmp_path / "r.json"
    runner.invoke(app, ["score", "--trace", TRACE, "-o", str(res), "--format", "json"])
    result = runner.invoke(app, ["report", "--results", str(res), "--format", "junit"])
    assert result.exit_code == 0
    assert "testsuite" in result.output


def test_aggregate_command(tmp_path: Path) -> None:
    r1 = tmp_path / "r1.json"
    r2 = tmp_path / "r2.json"
    runner.invoke(app, ["score", "--trace", TRACE, "-o", str(r1), "--format", "json"])
    runner.invoke(app, ["score", "--trace", TRACE, "-o", str(r2), "--format", "json"])
    result = runner.invoke(app, ["aggregate", str(r1), str(r2), "--label", "demo", "--format", "json"])
    assert result.exit_code in (0, 2)
    assert "reliability" in result.output or "pass_hat_k" in result.output


def test_gate_command_fails_strict_policy(tmp_path: Path) -> None:
    res = tmp_path / "r.json"
    runner.invoke(app, ["score", "--trace", TRACE, "-o", str(res), "--format", "json"])
    policy = tmp_path / "policy.yaml"
    policy.write_text("name: strict\nmin_ninja_score: 99\nrequired_certification: PASS\n")
    result = runner.invoke(app, ["gate", "--results", str(res), "--policy", str(policy)])
    assert result.exit_code == 2
    assert "FAILED" in result.output


def test_gate_command_passes_lenient_policy(tmp_path: Path) -> None:
    res = tmp_path / "r.json"
    runner.invoke(app, ["score", "--trace", TRACE, "-o", str(res), "--format", "json"])
    policy = tmp_path / "policy.yaml"
    policy.write_text("name: lenient\nmin_ninja_score: 1\n")
    result = runner.invoke(app, ["gate", "--results", str(res), "--policy", str(policy)])
    assert result.exit_code == 0
    assert "PASSED" in result.output


def test_run_command_replay(tmp_path: Path) -> None:
    out = tmp_path / "report.json"
    result = runner.invoke(
        app, ["run", "--task", TASK, "--replay", TRACE, "-o", str(out), "--format", "json"]
    )
    assert result.exit_code in (0, 2)
    assert "manifest" in result.output
    assert out.exists()


def test_run_command_with_solver_cmd() -> None:
    result = runner.invoke(
        app,
        ["run", "--task", TASK, "--solver-cmd", f"{sys.executable} {ECHO_AGENT}", "--seed", "5", "--format", "json"],
    )
    # Echo agent is trivial; certification may be FAIL (exit 2) — both fine.
    assert result.exit_code in (0, 2)
    assert "EchoAgent" in result.output
    assert "trace_sha256" in result.output


def test_run_command_requires_solver() -> None:
    result = runner.invoke(app, ["run", "--task", TASK])
    assert result.exit_code == 1
    assert "solver-cmd" in result.output or "replay" in result.output


def test_run_repeat_reliability(tmp_path: Path) -> None:
    base = tmp_path / "base.json"
    result = runner.invoke(
        app,
        ["run", "--task", TASK, "--solver-cmd", f"{sys.executable} {ECHO_AGENT}",
         "--repeat", "3", "--save-baseline", str(base), "--format", "json"],
    )
    assert result.exit_code in (0, 2)
    assert "reliability" in result.output or "pass_hat_k" in result.output
    assert base.exists()


def test_suite_summary_format() -> None:
    result = runner.invoke(
        app, ["suite", "--suite", "examples/scenarios/suite.yaml", "--format", "summary"]
    )
    assert result.exit_code in (0, 2)
    assert "Ninja Harness eval" in result.output


def test_serve_command_registered() -> None:
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    assert "playground" in result.output.lower()


def test_view_command_writes_html(tmp_path: Path) -> None:
    out = tmp_path / "trace.html"
    result = runner.invoke(app, ["view", "--trace", TRACE, "--case", CASE, "-o", str(out)])
    assert result.exit_code == 0
    assert out.exists()
    content = out.read_text()
    assert content.startswith("<!DOCTYPE html>")
    assert "ResearchAgent" in content


def test_calibrate_command(tmp_path: Path) -> None:
    # Build a results file from two scored traces, then calibrate against labels.
    r1 = tmp_path / "e1.json"
    runner.invoke(app, ["eval", "--trace", TRACE, "--case", CASE, "-o", str(r1), "--format", "json"])
    import json as _json

    results = [_json.loads(r1.read_text())]
    results_file = tmp_path / "results.json"
    results_file.write_text(_json.dumps(results))

    run_id = results[0]["run_id"]
    labels_file = tmp_path / "labels.json"
    labels_file.write_text(_json.dumps([{"run_id": run_id, "metric": "goal_success", "human_score": 0.6}]))

    result = runner.invoke(
        app, ["calibrate", "--results", str(results_file), "--labels", str(labels_file), "--format", "json"]
    )
    assert result.exit_code == 0
    assert "mean_abs_error" in result.output
