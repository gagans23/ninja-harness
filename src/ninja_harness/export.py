"""
export — turn graded agent runs into training-ready trajectories.

Ninja Harness *grades* agent runs; this module turns the high-scoring ones into a
curated dataset for fine-tuning the next generation of tool-calling agents. The
key idea is **honest curation**: an example is only exported if its run cleared a
quality bar (certification PASS and/or a minimum NARI score), and the score +
certification travel with every example. We never fabricate scores or
trajectories — we serialize what actually happened, filtered by what actually
passed.

Two output shapes:

* ``messages`` — OpenAI-style chat turns (user → assistant tool calls → tool
  results → final assistant), suited to tool-calling SFT.
* ``sft`` — a flat ``{prompt, completion}`` pair.

Optional **compression** trims low-signal steps (drop observations, cap step
count) so long trajectories shrink without changing the task or the final answer.

Deterministic and dependency-light: pure transforms over ``AgentRun`` /
``EvaluationResult``. No LLM calls.
"""

from __future__ import annotations

import json
from pathlib import Path

from ninja_harness.schemas import (
    AgentRun,
    EvaluationResult,
    TrajectoryExample,
    TrajectoryExportSummary,
)

VALID_FORMATS = ("messages", "sft")


def compress_run(
    run: AgentRun,
    *,
    max_steps: int | None = None,
    drop_observations: bool = False,
) -> AgentRun:
    """Return a copy of ``run`` with low-signal steps trimmed. The task, tool
    calls, and final output are preserved — only reasoning *steps* are reduced."""
    steps = list(run.steps)
    if drop_observations:
        steps = [s for s in steps if s.step_type != "observation"]
    if max_steps is not None and max_steps >= 0:
        steps = steps[:max_steps]
    return run.model_copy(update={"steps": steps})


def to_messages(run: AgentRun) -> list[dict]:
    """Serialize a run as OpenAI-style chat messages.

    Order: the task as the user turn; each non-final reasoning step with output
    as an assistant turn; each tool call as an assistant ``tool_calls`` turn
    followed by a ``tool`` result turn; finally the answer as an assistant turn.
    This is a deterministic serialization of the recorded run, not a claim about
    exact temporal interleaving of steps and tool calls.
    """
    final = (run.final_output or "").strip()
    messages: list[dict] = [{"role": "user", "content": run.task}]
    for step in run.steps:
        out = (step.output or "").strip()
        if not out or out == final or step.step_type == "final":
            continue
        messages.append({"role": "assistant", "content": out})
    for i, tc in enumerate(run.tool_calls):
        call_id = f"call_{i}"
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": call_id,
                "type": "function",
                "function": {
                    "name": tc.tool_name,
                    "arguments": json.dumps(tc.arguments, sort_keys=True),
                },
            }],
        })
        messages.append({
            "role": "tool",
            "tool_call_id": call_id,
            "content": "" if tc.result is None else str(tc.result),
        })
    messages.append({"role": "assistant", "content": final})
    return messages


def build_example(
    run: AgentRun,
    result: EvaluationResult,
    *,
    fmt: str = "messages",
) -> TrajectoryExample:
    """Build one training example from a run + its evaluation result."""
    if fmt not in VALID_FORMATS:
        raise ValueError(f"unknown format '{fmt}' (use one of {VALID_FORMATS})")
    ex = TrajectoryExample(
        run_id=run.run_id,
        task=run.task,
        ninja_score=result.ninja_score,
        certification=result.certification,
        format=fmt,
        metadata={
            "agent_name": run.agent_name,
            "grade": result.grade,
            "num_steps": len(run.steps),
            "num_tool_calls": len(run.tool_calls),
        },
    )
    if fmt == "messages":
        ex.messages = to_messages(run)
    else:  # sft
        ex.prompt = run.task
        ex.completion = (run.final_output or "").strip()
    return ex


def qualifies(
    result: EvaluationResult,
    *,
    min_score: float = 0.0,
    require_pass: bool = True,
) -> bool:
    """Whether a graded run is good enough to become a training example."""
    if require_pass and result.certification != "PASS":
        return False
    return result.ninja_score >= min_score


def export_runs(
    pairs: list[tuple[AgentRun, EvaluationResult]],
    *,
    fmt: str = "messages",
    min_score: float = 0.0,
    require_pass: bool = True,
    max_steps: int | None = None,
    drop_observations: bool = False,
) -> tuple[list[TrajectoryExample], TrajectoryExportSummary]:
    """Filter graded runs by quality and serialize the survivors.

    Returns (examples, summary). The summary reports how many candidates were
    considered, exported, and skipped — so the curation is auditable.
    """
    if fmt not in VALID_FORMATS:
        raise ValueError(f"unknown format '{fmt}' (use one of {VALID_FORMATS})")
    examples: list[TrajectoryExample] = []
    by_cert: dict[str, int] = {}
    for run, result in pairs:
        by_cert[result.certification] = by_cert.get(result.certification, 0) + 1
        if not qualifies(result, min_score=min_score, require_pass=require_pass):
            continue
        prepared = run
        if drop_observations or max_steps is not None:
            prepared = compress_run(run, max_steps=max_steps,
                                    drop_observations=drop_observations)
        examples.append(build_example(prepared, result, fmt=fmt))
    summary = TrajectoryExportSummary(
        total_candidates=len(pairs),
        exported=len(examples),
        skipped=len(pairs) - len(examples),
        format=fmt,
        min_score=min_score,
        require_pass=require_pass,
        by_certification=by_cert,
    )
    return examples, summary


def write_jsonl(examples: list[TrajectoryExample], path: str | Path) -> Path:
    """Write examples as JSON Lines (one example per line). Returns the path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex.model_dump(exclude_none=True), ensure_ascii=False) + "\n")
    return path
