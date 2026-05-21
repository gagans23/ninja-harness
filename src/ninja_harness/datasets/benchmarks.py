"""
Benchmark dataset loaders.

Maps the on-disk formats of well-known agent benchmarks into Ninja Harness
EvaluationCases so you can evaluate traces against recognized task definitions.

IMPORTANT — bring your own dataset:
These loaders read the *file formats* of SWE-bench, tau-bench, and GAIA. They do
NOT bundle the datasets (which are large and/or access-gated) and they make NO
benchmark-score claims. Download the datasets from their official sources and
point these loaders at the files.

- SWE-bench:  https://www.swebench.com/  (instances: instance_id, problem_statement, repo, ...)
- tau-bench:  https://github.com/sierra-research/tau-bench  (tasks: instruction, actions, outputs)
- GAIA:       https://huggingface.co/datasets/gaia-benchmark/GAIA  (rows: task_id, Question, Final answer, Level)

Note: properly *scoring* SWE-bench requires executing tests in a built repo
environment, and tau-bench requires its tool/database environment. These loaders
provide the task definitions; full execution scoring is out of scope here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ninja_harness.schemas import EvaluationCase, ToolCall


def _read_records(path: str | Path) -> list[dict]:
    """Read a JSON list or JSON Lines file into a list of dicts."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Benchmark file not found: {p}")
    text = p.read_text().strip()
    if not text:
        return []
    if p.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    data = json.loads(text)
    if isinstance(data, dict):
        # Some dumps wrap rows under a key; take the first list value.
        for v in data.values():
            if isinstance(v, list):
                return v
        return [data]
    return data


def load_swebench(path: str | Path) -> list[EvaluationCase]:
    """Load SWE-bench instances (JSON/JSONL) into EvaluationCases."""
    cases: list[EvaluationCase] = []
    for row in _read_records(path):
        cases.append(
            EvaluationCase(
                case_id=str(row.get("instance_id", row.get("id", "swebench"))),
                task=str(row.get("problem_statement", "")),
                metadata={
                    "benchmark": "swebench",
                    "repo": row.get("repo"),
                    "base_commit": row.get("base_commit"),
                    "version": row.get("version"),
                    "environment_setup_commit": row.get("environment_setup_commit"),
                    "FAIL_TO_PASS": row.get("FAIL_TO_PASS"),
                    "PASS_TO_PASS": row.get("PASS_TO_PASS"),
                    "has_test_patch": bool(row.get("test_patch")),
                },
            )
        )
    return cases


def load_gaia(path: str | Path) -> list[EvaluationCase]:
    """Load GAIA rows (JSON/JSONL) into EvaluationCases."""
    cases: list[EvaluationCase] = []
    for row in _read_records(path):
        # GAIA uses 'Final answer' (with a space) for the gold answer.
        answer = row.get("Final answer", row.get("final_answer"))
        cases.append(
            EvaluationCase(
                case_id=str(row.get("task_id", row.get("id", "gaia"))),
                task=str(row.get("Question", row.get("question", ""))),
                expected_output=str(answer) if answer is not None else None,
                metadata={
                    "benchmark": "gaia",
                    "level": row.get("Level", row.get("level")),
                    "file_name": row.get("file_name"),
                },
            )
        )
    return cases


def load_taubench(path: str | Path) -> list[EvaluationCase]:
    """Load tau-bench tasks (JSON/JSONL) into EvaluationCases."""
    cases: list[EvaluationCase] = []
    for i, row in enumerate(_read_records(path)):
        actions = row.get("actions", [])
        expected_tool_calls = [
            ToolCall(
                tool_name=str(a.get("name", "unknown_tool")),
                arguments=_coerce_args(a.get("kwargs", a.get("arguments", {}))),
            )
            for a in actions
            if isinstance(a, dict)
        ]
        outputs = row.get("outputs", [])
        references = [str(o) for o in outputs] if isinstance(outputs, list) else []
        cases.append(
            EvaluationCase(
                case_id=str(row.get("user_id", row.get("id", f"taubench-{i}"))),
                task=str(row.get("instruction", "")),
                expected_tool_calls=expected_tool_calls,
                references=references,
                metadata={
                    "benchmark": "taubench",
                    "annotator": row.get("annotator"),
                },
            )
        )
    return cases


def _coerce_args(args: Any) -> dict:
    return args if isinstance(args, dict) else {"_raw": args}


_LOADERS = {
    "swebench": load_swebench,
    "swe-bench": load_swebench,
    "gaia": load_gaia,
    "taubench": load_taubench,
    "tau-bench": load_taubench,
}


def load_benchmark(name: str, path: str | Path) -> list[EvaluationCase]:
    """Load a benchmark by name ('swebench' | 'gaia' | 'taubench')."""
    key = name.lower()
    if key not in _LOADERS:
        raise ValueError(
            f"Unknown benchmark {name!r}. Supported: {sorted(set(_LOADERS))}."
        )
    return _LOADERS[key](path)
