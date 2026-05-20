"""
Quickstart example — run a full evaluation programmatically.

Usage:
    python examples/quickstart.py
"""

from __future__ import annotations

from pathlib import Path

from ninja_harness.runner import EvaluationRunner
from ninja_harness.report import generate_markdown_report

TRACE = Path("src/ninja_harness/examples/simple_agent_trace.json")
CASE = Path("src/ninja_harness/examples/evaluation_case.yaml")


def main() -> None:
    runner = EvaluationRunner()
    run_obj, case_obj, result = runner.run_from_files(TRACE, CASE)

    print(f"Run ID   : {result.run_id}")
    print(f"Score    : {result.ninja_score:.1f} / 100")
    print(f"Grade    : {result.grade}")
    print(f"Status   : {result.certification}")
    print()

    for mr in result.metric_results:
        score_str = "N/A" if not mr.is_applicable else f"{mr.score:.3f}"
        print(f"  {mr.name:<25} {score_str}")

    print()
    print("--- Markdown Report ---")
    print(generate_markdown_report(result, run=run_obj))


if __name__ == "__main__":
    main()
