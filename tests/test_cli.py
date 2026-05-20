"""CLI smoke tests using Typer's test runner."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ninja_harness.cli import app

TRACE = str(Path("src/ninja_harness/examples/simple_agent_trace.json"))
CASE = str(Path("src/ninja_harness/examples/evaluation_case.yaml"))
FAILING_TRACE = str(Path("src/ninja_harness/examples/failing_agent_trace.json"))
SUITE = str(Path("src/ninja_harness/examples/example_suite.yaml"))
OPENAI_TRACE = str(Path("src/ninja_harness/examples/openai_agents_trace.json"))

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
