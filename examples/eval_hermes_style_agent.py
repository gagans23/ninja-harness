"""
Hermes-style multi-agent trace evaluation example.

This shows how to evaluate a trace where multiple agents collaborate
via structured handoffs — a common pattern in production multi-agent systems.

Usage:
    python examples/eval_hermes_style_agent.py
"""

from __future__ import annotations

from pathlib import Path

from ninja_harness.runner import EvaluationRunner
from ninja_harness.report import generate_markdown_report

TRACE = Path("src/ninja_harness/examples/hermes_style_trace.json")


def main() -> None:
    runner = EvaluationRunner()
    # No eval case — standalone scoring
    run_obj, _, result = runner.run_from_files(TRACE)

    print("=== Hermes-Style Multi-Agent Evaluation ===\n")
    print(f"Agent    : {run_obj.agent_name}")
    print(f"Task     : {run_obj.task}")
    print(f"Handoffs : {len(run_obj.handoffs)}")
    print()
    print(f"Ninja Score  : {result.ninja_score:.1f} / 100")
    print(f"Grade        : {result.grade}")
    print(f"Certification: {result.certification}")
    print()

    handoff_metric = result.metric_by_name("handoff_integrity")
    if handoff_metric and handoff_metric.is_applicable:
        print(f"Handoff Integrity Score: {handoff_metric.score:.3f}")
        per = handoff_metric.details.get("per_handoff_scores", [])
        for h in per:
            print(
                f"  Handoff {h['index']}: {h['source']} → {h['target']} "
                f"(score={h['score']}, missing={h['missing_fields']})"
            )
    print()

    if result.top_failure_reasons:
        print("Failure Reasons:")
        for reason in result.top_failure_reasons:
            print(f"  • {reason}")

    print()
    print("--- Full Markdown Report ---")
    print(generate_markdown_report(result, run=run_obj))


if __name__ == "__main__":
    main()
