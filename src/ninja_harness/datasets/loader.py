"""Utilities for loading traces and evaluation cases from disk."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from ninja_harness.schemas import AgentRun, EvaluationCase, SuiteSpec


def load_trace(path: str | Path) -> dict:
    """Load a raw trace dict from a JSON file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Trace file not found: {p}")
    if p.suffix.lower() != ".json":
        raise ValueError(f"Trace files must be JSON (.json), got: {p.suffix}")
    with p.open() as f:
        return json.load(f)


def load_eval_case(path: str | Path) -> EvaluationCase:
    """Load an EvaluationCase from a YAML or JSON file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Eval case file not found: {p}")

    with p.open() as f:
        if p.suffix.lower() in {".yaml", ".yml"}:
            raw = yaml.safe_load(f)
        elif p.suffix.lower() == ".json":
            raw = json.load(f)
        else:
            raise ValueError(
                f"Eval case files must be YAML or JSON, got: {p.suffix}"
            )

    return EvaluationCase.model_validate(raw)


def load_agent_run_from_file(path: str | Path) -> AgentRun:
    """Load a fully parsed AgentRun from a JSON file (Ninja Harness native format)."""
    raw = load_trace(path)
    return AgentRun.model_validate(raw)


def load_suite(path: str | Path) -> SuiteSpec:
    """
    Load an evaluation SuiteSpec from a YAML or JSON file.

    Relative trace/case paths inside the suite are resolved relative to the
    suite file's own directory.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Suite file not found: {p}")

    with p.open() as f:
        if p.suffix.lower() in {".yaml", ".yml"}:
            raw = yaml.safe_load(f)
        elif p.suffix.lower() == ".json":
            raw = json.load(f)
        else:
            raise ValueError(f"Suite files must be YAML or JSON, got: {p.suffix}")

    spec = SuiteSpec.model_validate(raw)

    base_dir = p.parent
    for c in spec.cases:
        c.trace = str((base_dir / c.trace).resolve()) if not Path(c.trace).is_absolute() else c.trace
        if c.case and not Path(c.case).is_absolute():
            c.case = str((base_dir / c.case).resolve())
    if spec.baseline and not Path(spec.baseline).is_absolute():
        spec.baseline = str((base_dir / spec.baseline).resolve())

    return spec
