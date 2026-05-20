"""Ninja Harness CLI — powered by Typer and Rich."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ninja_harness import __version__
from ninja_harness.adapters import detect_adapter
from ninja_harness.datasets.loader import load_task, load_trace
from ninja_harness.policy import apply_policy, load_policy
from ninja_harness.redteam import run_all_checks
from ninja_harness.report import (
    generate_json_report,
    generate_markdown_report,
    generate_suite_json_report,
    generate_suite_markdown_report,
    save_report,
)
from ninja_harness.reporters import evaluation_to_junit, to_sarif
from ninja_harness.runner import EvaluationRunner, SuiteRunner, TaskExecutor
from ninja_harness.schemas import AgentRun, AggregateResult, EvaluationResult, SuiteResult
from ninja_harness.solver import CommandSolver, ScriptedSolver
from ninja_harness.statistics import aggregate_results

app = typer.Typer(
    name="ninja-harness",
    help="Trace-first evals for agents that need to survive production.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()

_CERT_STYLE = {"PASS": "bold green", "WARN": "bold yellow", "FAIL": "bold red"}
_CERT_EMOJI = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌"}


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"ninja-harness [bold cyan]{__version__}[/]")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None, "--version", "-V", callback=_version_callback, is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Ninja Harness — trace-first evals for production-grade agents."""


# ---------------------------------------------------------------------------
# eval command
# ---------------------------------------------------------------------------

@app.command()
def eval(
    trace: Path = typer.Option(..., help="Path to agent trace JSON file."),
    case: Path | None = typer.Option(None, help="Path to evaluation case YAML/JSON."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Save JSON results to file."),
    baseline: Path | None = typer.Option(None, help="Path to baseline results JSON for stability scoring."),
    save_baseline: Path | None = typer.Option(
        None, help="Save this run's results as a baseline JSON for future stability comparison."
    ),
    format: str = typer.Option("rich", help="Output format: rich | json | markdown."),
) -> None:
    """Evaluate an agent trace against an optional evaluation case."""
    runner = EvaluationRunner(baseline_path=str(baseline) if baseline else None)

    try:
        run_obj, case_obj, result = runner.run_from_files(trace, case)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[bold red]Error:[/] {exc}")
        raise typer.Exit(1) from exc

    if format == "json":
        console.print_json(generate_json_report(result))
    elif format == "markdown":
        console.print(generate_markdown_report(result, run=run_obj))
    else:
        _render_rich_result(result, run_obj)

    if output:
        save_report(generate_json_report(result), str(output))
        console.print(f"\n[dim]Results saved to:[/] {output}")

    if save_baseline:
        save_report(generate_json_report(result), str(save_baseline))
        console.print(f"[dim]Baseline saved to:[/] {save_baseline}")

    if result.certification == "FAIL":
        raise typer.Exit(2)


# ---------------------------------------------------------------------------
# score command
# ---------------------------------------------------------------------------

@app.command()
def score(
    trace: Path = typer.Option(..., help="Path to agent trace JSON file."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Save JSON results to file."),
    format: str = typer.Option("rich", help="Output format: rich | json | markdown."),
) -> None:
    """Score a trace without an evaluation case (standalone mode)."""
    runner = EvaluationRunner()

    try:
        run_obj, _, result = runner.run_from_files(trace, case_path=None)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[bold red]Error:[/] {exc}")
        raise typer.Exit(1) from exc

    if format == "json":
        console.print_json(generate_json_report(result))
    elif format == "markdown":
        console.print(generate_markdown_report(result, run=run_obj))
    else:
        _render_rich_result(result, run_obj)

    if output:
        save_report(generate_json_report(result), str(output))
        console.print(f"\n[dim]Results saved to:[/] {output}")


# ---------------------------------------------------------------------------
# validate command
# ---------------------------------------------------------------------------

@app.command()
def validate(
    trace: Path = typer.Option(..., help="Path to agent trace JSON file."),
) -> None:
    """Validate that a trace file parses against the AgentRun schema."""
    try:
        raw = load_trace(trace)
        adapter = detect_adapter(raw)
        run_obj = adapter.parse(raw)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[bold red]Validation failed:[/] {exc}")
        raise typer.Exit(1) from exc
    except Exception as exc:  # noqa: BLE001
        console.print(f"[bold red]Parse error:[/] {exc}")
        raise typer.Exit(1) from exc

    console.print(
        Panel(
            f"[bold green]✅ Valid[/]\n\n"
            f"  Adapter  : [cyan]{adapter.adapter_name}[/]\n"
            f"  Run ID   : [dim]{run_obj.run_id}[/]\n"
            f"  Agent    : {run_obj.agent_name}\n"
            f"  Steps    : {len(run_obj.steps)}\n"
            f"  Tools    : {len(run_obj.tool_calls)}\n"
            f"  Handoffs : {len(run_obj.handoffs)}",
            title="Ninja Harness — Trace Validation",
            border_style="green",
        )
    )


# ---------------------------------------------------------------------------
# redteam command
# ---------------------------------------------------------------------------

@app.command()
def redteam(
    trace: Path = typer.Option(..., help="Path to agent trace JSON file."),
    format: str = typer.Option("rich", help="Output format: rich | json."),
) -> None:
    """Run defensive red-team checks against a trace (detection-only)."""
    try:
        raw = load_trace(trace)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[bold red]Error:[/] {exc}")
        raise typer.Exit(1) from exc

    findings = run_all_checks(raw)

    if format == "json":
        console.print_json(json.dumps(findings, indent=2))
        if findings:
            raise typer.Exit(2)
        return

    if not findings:
        console.print(
            Panel(
                "[bold green]✅ No red-team findings.[/]\n\n"
                "No prompt injection, data exfiltration, tool misuse, or unsafe delegation "
                "patterns were detected in this trace.\n\n"
                "[dim]Note: Automated checks complement but do not replace human review.[/]",
                title="Ninja Harness — Red Team",
                border_style="green",
            )
        )
        return

    table = Table(
        "Check", "Severity", "OWASP", "Location", "Description",
        title="[bold red]Red Team Findings[/]",
        box=box.ROUNDED,
        show_lines=True,
    )
    sev_style = {"critical": "bold red", "high": "red", "medium": "yellow", "low": "dim"}

    for f in findings:
        sev = f.get("severity", "low")
        owasp_ids = ", ".join(o["id"] for o in f.get("standards", {}).get("owasp", []))
        table.add_row(
            f.get("check", ""),
            f"[{sev_style.get(sev, '')}]{sev.upper()}[/]",
            owasp_ids or "—",
            f.get("location", ""),
            f.get("description", "")[:70],
        )

    console.print(table)
    console.print(
        "\n[bold yellow]⚠️  Human review required.[/] "
        "Red-team checks are defensive detectors — verify findings before action."
    )
    raise typer.Exit(2)


# ---------------------------------------------------------------------------
# report command
# ---------------------------------------------------------------------------

@app.command()
def report(
    results: Path = typer.Option(..., help="Path to evaluation results JSON."),
    format: str = typer.Option("markdown", help="Output format: markdown | json | sarif | junit."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Save report to file."),
) -> None:
    """Generate a formatted report from saved evaluation results."""
    if not results.exists():
        console.print(f"[bold red]Error:[/] File not found: {results}")
        raise typer.Exit(1)

    with results.open() as f:
        raw = json.load(f)

    try:
        result = EvaluationResult.model_validate(raw)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[bold red]Invalid results file:[/] {exc}")
        raise typer.Exit(1) from exc

    if format == "markdown":
        content = generate_markdown_report(result)
    elif format == "sarif":
        content = to_sarif(result)
    elif format == "junit":
        content = evaluation_to_junit(result)
    else:
        content = generate_json_report(result)

    console.print(content)

    if output:
        save_report(content, str(output))
        console.print(f"\n[dim]Report saved to:[/] {output}")


# ---------------------------------------------------------------------------
# suite command
# ---------------------------------------------------------------------------

@app.command()
def suite(
    suite: Path = typer.Option(..., help="Path to a suite YAML/JSON file."),
    use_async: bool = typer.Option(False, "--async", help="Evaluate cases concurrently."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Save suite JSON results."),
    format: str = typer.Option("rich", help="Output format: rich | json | markdown."),
) -> None:
    """Run an evaluation suite over multiple trace/case pairs."""
    runner = SuiteRunner()

    try:
        suite_result = runner.run_suite_from_file(suite, use_async=use_async)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[bold red]Error:[/] {exc}")
        raise typer.Exit(1) from exc

    if format == "json":
        console.print_json(generate_suite_json_report(suite_result))
    elif format == "markdown":
        console.print(generate_suite_markdown_report(suite_result))
    else:
        _render_rich_suite(suite_result)

    if output:
        save_report(generate_suite_json_report(suite_result), str(output))
        console.print(f"\n[dim]Suite results saved to:[/] {output}")

    if suite_result.failed > 0 or suite_result.errors:
        raise typer.Exit(2)


# ---------------------------------------------------------------------------
# run command — end-to-end: drive an agent, capture, evaluate, certify
# ---------------------------------------------------------------------------

@app.command()
def run(
    task: Path = typer.Option(..., help="Path to a task YAML/JSON file."),
    solver_cmd: str | None = typer.Option(
        None, "--solver-cmd", help="Shell command for the agent (receives task JSON on stdin, prints trace JSON)."
    ),
    replay: Path | None = typer.Option(
        None, help="Replay a captured trace JSON instead of running an agent (ScriptedSolver)."
    ),
    seed: int | None = typer.Option(None, help="Seed recorded in the manifest and applied to the process."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Save the full RunReport JSON."),
    format: str = typer.Option("rich", help="Output format: rich | json."),
) -> None:
    """Drive an agent against a task, capture its trace, evaluate, and certify."""
    try:
        task_spec = load_task(task)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[bold red]Error:[/] {exc}")
        raise typer.Exit(1) from exc

    if replay:
        solver = ScriptedSolver(trace_path=str(replay))
    elif solver_cmd:
        import shlex

        solver = CommandSolver(shlex.split(solver_cmd))
    else:
        console.print("[bold red]Error:[/] provide either --solver-cmd or --replay.")
        raise typer.Exit(1)

    executor = TaskExecutor()
    try:
        report = executor.run(task_spec, solver, seed=seed)
    except (RuntimeError, ValueError, TypeError) as exc:
        console.print(f"[bold red]Run failed:[/] {exc}")
        raise typer.Exit(1) from exc

    if format == "json":
        console.print_json(report.model_dump_json(indent=2))
    else:
        _render_rich_result(report.result, report.run)
        m = report.manifest
        console.print(
            f"\n[dim]Manifest:[/] solver={m.solver} sandbox={m.sandbox} "
            f"seed={m.seed} trace_sha256={m.trace_sha256[:12]}… "
            f"git={(m.git_sha or 'n/a')[:8]}"
        )

    if output:
        save_report(report.model_dump_json(indent=2), str(output))
        console.print(f"[dim]Run report saved to:[/] {output}")

    if report.result.certification == "FAIL":
        raise typer.Exit(2)


# ---------------------------------------------------------------------------
# aggregate command
# ---------------------------------------------------------------------------

@app.command()
def aggregate(
    results: list[Path] = typer.Argument(..., help="Two or more EvaluationResult JSON files (repeated runs of the same task)."),
    label: str = typer.Option("aggregate", help="Label for the aggregated task."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Save AggregateResult JSON."),
    format: str = typer.Option("rich", help="Output format: rich | json."),
) -> None:
    """Aggregate repeated runs into reliability statistics (pass@k, pass^k, CIs)."""
    loaded: list[EvaluationResult] = []
    for path in results:
        if not path.exists():
            console.print(f"[bold red]Error:[/] File not found: {path}")
            raise typer.Exit(1)
        with path.open() as f:
            loaded.append(EvaluationResult.model_validate(json.load(f)))

    agg = aggregate_results(loaded, task_label=label)

    if format == "json":
        console.print_json(agg.model_dump_json(indent=2))
    else:
        _render_rich_aggregate(agg)

    if output:
        save_report(agg.model_dump_json(indent=2), str(output))
        console.print(f"\n[dim]Aggregate saved to:[/] {output}")

    if agg.verdict == "UNRELIABLE":
        raise typer.Exit(2)


# ---------------------------------------------------------------------------
# gate command
# ---------------------------------------------------------------------------

@app.command()
def gate(
    results: Path = typer.Option(..., help="EvaluationResult JSON to gate."),
    policy: Path = typer.Option(..., help="Policy YAML/JSON with thresholds."),
    baseline: Path | None = typer.Option(None, help="Baseline EvaluationResult JSON for regression checks."),
    format: str = typer.Option("rich", help="Output format: rich | json."),
) -> None:
    """Apply an evaluation policy as a CI gate (non-zero exit on violation)."""
    if not results.exists():
        console.print(f"[bold red]Error:[/] File not found: {results}")
        raise typer.Exit(1)

    with results.open() as f:
        result = EvaluationResult.model_validate(json.load(f))

    try:
        pol = load_policy(policy)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[bold red]Error:[/] {exc}")
        raise typer.Exit(1) from exc

    base = None
    if baseline and baseline.exists():
        with baseline.open() as f:
            base = EvaluationResult.model_validate(json.load(f))

    gate_result = apply_policy(result, pol, baseline=base)

    if format == "json":
        console.print_json(gate_result.model_dump_json(indent=2))
    else:
        if gate_result.passed:
            console.print(
                Panel(
                    f"[bold green]✅ Gate PASSED[/] under policy '{gate_result.policy_name}'",
                    border_style="green",
                )
            )
        else:
            lines = "\n".join(f"  • [{v.severity}] {v.rule}: {v.detail}" for v in gate_result.violations)
            console.print(
                Panel(
                    f"[bold red]❌ Gate FAILED[/] under policy '{gate_result.policy_name}'\n\n{lines}",
                    border_style="red",
                )
            )

    if not gate_result.passed:
        raise typer.Exit(2)


# ---------------------------------------------------------------------------
# Rich rendering helpers
# ---------------------------------------------------------------------------

def _render_rich_result(result: EvaluationResult, run: AgentRun | None = None) -> None:
    cert_style = _CERT_STYLE.get(result.certification, "white")
    cert_emoji = _CERT_EMOJI.get(result.certification, "")

    summary_lines = []
    if run:
        summary_lines.append(f"  Agent    : [bold]{run.agent_name}[/]")
        summary_lines.append(f"  Task     : {run.task[:70]}")
    summary_lines += [
        f"  Run ID   : [dim]{result.run_id}[/]",
        f"  Score    : [bold cyan]{result.ninja_score:.1f} / 100[/]",
        f"  Grade    : [bold]{result.grade}[/]",
        f"  Status   : [{cert_style}]{cert_emoji} {result.certification}[/]",
    ]

    console.print(
        Panel(
            "\n".join(summary_lines),
            title="[bold]Ninja Harness Evaluation[/]",
            border_style=cert_style,
        )
    )

    table = Table(
        "Metric", "Score", "Status", "Finding",
        box=box.SIMPLE_HEAVY,
        title="Metric Breakdown",
    )

    for mr in result.metric_results:
        score_str = "N/A" if not mr.is_applicable else f"{mr.score:.3f}"
        status_str = "SKIP" if not mr.is_applicable else ("PASS" if mr.passed else "FAIL")
        status_style = (
            "dim" if not mr.is_applicable
            else ("green" if mr.passed else "red")
        )
        finding = mr.failure_reasons[0][:60] if mr.failure_reasons else (
            mr.details.get("reason", "OK")[:60] if not mr.is_applicable else "No issues"
        )
        table.add_row(
            mr.name.replace("_", " ").title(),
            score_str,
            f"[{status_style}]{status_str}[/]",
            str(finding),
        )

    console.print(table)

    if result.top_failure_reasons:
        console.print("\n[bold red]Top Failure Reasons:[/]")
        for r in result.top_failure_reasons:
            console.print(f"  • {r}")

    if result.recommended_fixes:
        console.print("\n[bold yellow]Recommended Fixes:[/]")
        for fix in result.recommended_fixes:
            console.print(f"  → {fix}")


def _render_rich_suite(suite: SuiteResult) -> None:
    pass_style = "green" if suite.pass_rate >= 0.8 else ("yellow" if suite.pass_rate >= 0.5 else "red")

    console.print(
        Panel(
            f"  Suite        : [bold]{suite.name}[/]\n"
            f"  Cases        : {suite.total}\n"
            f"  Passed       : [green]{suite.passed}[/]   "
            f"Warned: [yellow]{suite.warned}[/]   "
            f"Failed: [red]{suite.failed}[/]   "
            f"Errors: [red]{len(suite.errors)}[/]\n"
            f"  Pass rate    : [{pass_style}]{suite.pass_rate:.0%}[/]\n"
            f"  Avg score    : [bold cyan]{suite.average_score:.1f} / 100[/]",
            title="[bold]Ninja Harness Suite[/]",
            border_style=pass_style,
        )
    )

    table = Table(
        "Run ID", "Score", "Grade", "Certification",
        box=box.SIMPLE_HEAVY,
        title="Suite Cases",
    )
    for r in suite.results:
        cert_style = _CERT_STYLE.get(r.certification, "white")
        table.add_row(
            r.run_id,
            f"{r.ninja_score:.1f}",
            r.grade,
            f"[{cert_style}]{r.certification}[/]",
        )
    console.print(table)

    if suite.errors:
        console.print("\n[bold red]Errors:[/]")
        for e in suite.errors:
            console.print(f"  • {e.get('trace')}: {e.get('error')}")


def _render_rich_aggregate(agg: AggregateResult) -> None:
    s = agg.reliability
    verdict_style = {
        "RELIABLE": "bold green",
        "FLAKY": "bold yellow",
        "UNRELIABLE": "bold red",
    }.get(agg.verdict, "white")

    console.print(
        Panel(
            f"  Task        : [bold]{agg.task_label}[/]\n"
            f"  Trials      : {s.trials}\n"
            f"  Mean score  : [bold cyan]{s.mean_score:.1f}[/] "
            f"(95% CI {s.ci_low:.1f}–{s.ci_high:.1f}, std {s.std_score:.1f})\n"
            f"  Range       : {s.min_score:.1f} – {s.max_score:.1f}\n"
            f"  pass@k      : {s.pass_at_k:.2f}    pass^k: [bold]{s.pass_hat_k:.2f}[/]\n"
            f"  Consistency : {s.consistency:.2f}\n"
            f"  Verdict     : [{verdict_style}]{agg.verdict}[/]",
            title="[bold]Ninja Harness Reliability[/]",
            border_style=verdict_style,
        )
    )
    if agg.notes:
        console.print("\n[bold]Notes:[/]")
        for n in agg.notes:
            console.print(f"  • {n}")


if __name__ == "__main__":
    app()
